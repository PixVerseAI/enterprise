"""国内、海外共用的 HTTP 传输、认证和响应处理。"""

import mimetypes
import re
from pathlib import Path
from uuid import uuid4

import httpx

from . import __version__
from .config import Config
from .protocol import https_url

SENSITIVE_KEYS = {
    "apikey",
    "token",
    "accesstoken",
    "refreshtoken",
    "authorization",
    "cookie",
    "setcookie",
    "password",
    "secret",
    "webhooksecret",
    "signature",
    "credential",
}


def redact(value, api_key=""):
    """递归清理凭据；签名链接保留供用户取片，URL 中显式认证参数清理。"""
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if re.sub(r"[^a-z0-9]", "", k.lower()) in SENSITIVE_KEYS
            else redact(v, api_key)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v, api_key) for v in value]
    if isinstance(value, str):
        if api_key:
            value = value.replace(api_key, "[REDACTED]")
        value = re.sub(
            r"(?i)([?&](?:api[-_]?key|token|access_token|authorization|password|secret)=)[^&#\s]+",
            r"\1[REDACTED]",
            value,
        )
        value = re.sub(
            r"(?i)((?:API[-_]?KEY|Authorization|Cookie)\s*[:=]\s*)[^\r\n,;]+",
            r"\1[REDACTED]",
            value,
        )
    return value


class APIError(Exception):
    def __init__(self, kind, message, *, trace_id=None, http_status=None, response=None,
                 stage=None, submission_state=None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.trace_id = trace_id
        self.http_status = http_status
        self.response = response
        self.stage = stage
        self.submission_state = submission_state

    def as_dict(self):
        result = {
            "type": self.kind,
            "message": self.message,
            "trace_id": self.trace_id,
            "http_status": self.http_status,
            "response": self.response,
        }
        if self.stage is not None:
            result.update(stage=self.stage, submission_state=self.submission_state)
        return result


class PlatformClient:
    def __init__(self, config: Config, *, timeout=60.0, transport=None, read_only=False):
        self.config = config
        self.read_only = read_only
        self.request_count = 0
        self.write_attempted = False
        self.last_context = {}
        # 禁止跳转和隐式代理，防止 API Key 被转发到其他地域或任意地址。
        self.http = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.http.close()

    def request(self, method, path, *, allow_empty_resp=False, **kwargs):
        """共用响应校验；仅明确声明的空结果接口允许Resp为null。"""
        trace_id = str(uuid4())
        self.request_count += 1
        self.write_attempted = self.write_attempted or (
            not self.read_only and method.upper() not in ("GET", "HEAD", "OPTIONS")
        )
        self.last_context = {"trace_id": trace_id}
        try:
            response = self.http.request(
                method,
                self.config.base_url + path,
                headers={
                    "API-KEY": self.config.api_key,
                    "Ai-trace-id": trace_id,
                    "PixVerse-Client": "cli",
                    "User-Agent": f"pixverse-cli/{__version__}",
                },
                **kwargs,
            )
        except httpx.TimeoutException:
            raise APIError(
                "timeout",
                "请求超时，结果未确认。写请求可能已受理，请勿直接重复提交。",
                trace_id=trace_id,
            ) from None
        except httpx.HTTPError:
            raise APIError(
                "network",
                "网络请求失败，结果未确认。请保留 trace_id 排查后再决定是否重试。",
                trace_id=trace_id,
            ) from None

        try:
            body = response.json()
        except ValueError:
            body = None
        safe_body = redact(body, self.config.api_key)
        error_context = dict(
            trace_id=trace_id,
            http_status=response.status_code,
            response=safe_body,
        )
        self.last_context = error_context
        detail = safe_body.get("Error") if isinstance(safe_body, dict) else None
        message = detail.get("Message") if isinstance(detail, dict) else None
        if not isinstance(message, str) or not message:
            message = safe_body.get("ErrMsg") if isinstance(safe_body, dict) else None
        message = message if isinstance(message, str) and message else None
        if not response.is_success:
            raise APIError("http", message or "API 返回非成功 HTTP 状态。", **error_context)
        if not isinstance(body, dict) or type(body.get("ErrCode")) is not int:
            raise APIError("protocol", "API 响应缺少有效的 ErrCode。", **error_context)
        if body["ErrCode"] != 0:
            raise APIError("business", message or "API 业务请求失败，请查看 response。",
                           **error_context)
        if not isinstance(body.get("Resp"), dict) and not (
            allow_empty_resp and "Resp" in body and body["Resp"] is None
        ):
            raise APIError("protocol", "API 响应缺少有效的 Resp。", **error_context)
        return {
            "region": self.config.region,
            "environment": "production",
            "trace_id": trace_id,
            "http_status": response.status_code,
            "response": safe_body,
        }

    def balance(self):
        return self.request("GET", "/openapi/v2/account/balance")

    def upload(self, kind, *, file=None, url=None):
        if (file is None) == (url is None):
            raise ValueError("--file 和 --url 必须且只能提供一个。")
        image = kind == "image"
        path = "/openapi/v2/image/upload" if image else "/openapi/v2/media/upload"
        field = "image" if image else "file"
        if url is not None:
            if not https_url(url):
                raise ValueError("--url 必须是有效 HTTPS 地址，不能含凭据、片段或非443端口。")
            # 即使仅提供 URL，也按文档发送 multipart/form-data。
            result = self.request("POST", path, files={field + "_url": (None, url)})
        else:
            source = Path(file)
            mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            with source.open("rb") as stream:
                result = self.request("POST", path, files={field: (source.name, stream, mime)})
        id_field = "img_id" if image else "media_id"
        identifier = result["response"]["Resp"].get(id_field)
        if type(identifier) is not int or not 0 < identifier < 2**64:
            raise APIError("protocol", f"上传响应缺少有效{id_field}，请核查后再决定是否重试。",
                           trace_id=result["trace_id"], http_status=result["http_status"],
                           response=result["response"])
        return result

    def generate(self, payload, *, image=False):
        kind = "img" if image else "text"
        return self.submit(f"video/{kind}/generate", payload)

    def submit(self, endpoint, payload):
        result = self.request("POST", f"/openapi/v2/{endpoint}", json=payload)
        identifier = result["response"]["Resp"].get("video_id")
        if type(identifier) is not int or not 0 < identifier < 2**64:
            raise APIError(
                "protocol",
                "创建响应缺少 video_id，请核查后再决定是否重新提交。",
                trace_id=result["trace_id"],
                http_status=result["http_status"],
                response=result["response"],
            )
        result["submission"] = "accepted"
        return result

    def task(self, video_id):
        result = self.request("GET", f"/openapi/v2/video/result/{video_id}")
        status = result["response"]["Resp"].get("status")
        if type(status) not in (int, str):
            raise APIError(
                "protocol",
                "任务响应缺少有效的 status。",
                trace_id=result["trace_id"],
                http_status=result["http_status"],
                response=result["response"],
            )
        states = {
            1: "completed",
            5: "generating",
            7: "moderation_failed",
            8: "failed",
            "succeeded": "completed",
            "running": "generating",
            "pending": "generating",
            "queued": "generating",
            "failed": "failed",
            "canceled": "failed",
            "cancelled": "failed",
        }
        # 未知整数/字符串状态保留原响应，不能推断成功。
        result["task_status"] = states.get(status, "unknown")
        resp = result["response"]["Resp"]
        output = resp.get("output")
        result["output_url"] = (
            (resp.get("url") or (output.get("video") if isinstance(output, dict) else None))
            if result["task_status"] == "completed"
            else None
        )
        # 仅忠实返回 API 状态，不额外访问成片 URL 或声称已验证可访问。
        result["output_url_verified"] = False
        return result
