"""CLI业务执行入口，不依赖命令行上下文或输出流。"""

from .client import APIError, PlatformClient
from .protocol import InputError, prepare_arguments

READ_ONLY = frozenset({"account_balance", "account_usage", "video_get", "video_restyle_list",
                       "voice_list", "template_list", "template_get"})


def failure_context(name, client=None, *, kind=None):
    """只根据本次是否实际尝试写入判断状态，不能从错误文案猜测副作用。"""
    if name in READ_ONLY:
        return {"stage": "validation" if client is None else "upstream",
                "submission_state": "not_applicable"}
    if client is None or not client.write_attempted:
        stage = "discovery" if client is not None and client.request_count else "validation"
        return {"stage": stage,
                "submission_state": "not_submitted"}
    return {"stage": "upstream",
            "submission_state": "rejected" if kind == "business" else "unknown"}


def execute_operation(handler, config, parameters, *, name, timeout=60.0,
                      client_factory=PlatformClient):
    """每次调用独立创建客户端，固定认证配置并保持单次请求语义。"""
    parameters = prepare_arguments(name, parameters)
    with client_factory(config, timeout=timeout, read_only=name in READ_ONLY) as client:
        try:
            result = handler(client, **parameters)
        except APIError as exc:
            context = failure_context(name, client, kind=exc.kind)
            exc.stage, exc.submission_state = context["stage"], context["submission_state"]
            raise
        except (ValueError, OSError) as exc:
            error = exc if isinstance(exc, InputError) else InputError(
                "本地文件无法读取，请检查路径和权限。" if isinstance(exc, OSError) else str(exc)
            )
            error.detail.update(client.last_context)
            if client.request_count and not client.write_attempted:
                error.detail["discovery_trace_id"] = client.last_context.get("trace_id")
            error.detail.update(failure_context(name, client))
            raise error from None
        except Exception:
            raise APIError("internal", "服务处理失败。", **client.last_context,
                           **failure_context(name, client)) from None
        result.update(stage="result" if name in READ_ONLY else "accepted",
                      submission_state="not_applicable" if name in READ_ONLY else "accepted")
        return result
