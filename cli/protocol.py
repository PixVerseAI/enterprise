"""统一执行公开 Schema 校验，返回不包含原始输入的具体协议错误。"""

import json
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

FORMATS = FormatChecker()
SCHEMAS = json.loads(files("cli").joinpath("schemas.json").read_text(encoding="utf-8"))


class InputError(ValueError):
    """协议错误仅携带固定说明、字段名和协议声明的允许值。"""

    def __init__(self, message, fields=(), *, code="INVALID_ARGUMENT", allowed_values=None):
        """构造可返回给客户端的安全协议错误。"""
        super().__init__(message)
        self.detail = {
            "type": "validation",
            "code": code,
            "message": message,
            "fields": list(fields),
        }
        if allowed_values is not None:
            self.detail["allowed_values"] = allowed_values


@FORMATS.checks("pixverse-https-url")
def https_url(value):
    """仅校验公开 URL 语法，不解析 DNS、抓取文件或限制供应商域名。"""
    if not isinstance(value, str):
        return True
    try:
        parsed = urlsplit(value)
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and parsed.port in (None, 443)
            and not parsed.username
            and not parsed.password
            and not parsed.fragment
            and not any(char.isspace() for char in value)
        )
    except ValueError:
        return False


@FORMATS.checks("pixverse-date-time")
def date_time(value):
    """校验接口日期格式，时间窗口与时区业务由 Platform 判定。"""
    if not isinstance(value, str):
        return True
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S") == value
    except ValueError:
        return False


def _field(path):
    """将 Schema 字段路径转换为可读字段名，不使用请求值生成文案。"""
    return ".".join(map(str, path)) or "$"


def _detail(error):
    """从 Schema 约束生成安全错误，不采用可能包含原始值的库错误文本。"""
    path = list(error.absolute_path)
    field = _field(path)
    if "x-error-message" in error.schema:
        return InputError(
            error.schema["x-error-message"],
            error.schema.get("x-error-fields", ()),
            code="FIELD_COMBINATION",
        )
    if error.validator in ("anyOf", "oneOf") and error.context:
        specific = [e for e in error.context if e.validator != "type"]
        return _detail((specific or error.context)[0])
    if error.validator == "required":
        missing = next(key for key in error.validator_value if key not in error.instance)
        field = _field(path + [missing])
        return InputError(f"缺少必填字段 {field}。", (field,), code="FIELD_REQUIRED")
    if error.validator == "enum":
        return InputError(
            f"字段 {field} 不在协议允许值中。",
            (field,),
            code="FIELD_ENUM",
            allowed_values=error.validator_value,
        )
    if error.validator == "type":
        return InputError(
            f"字段 {field} 的类型必须为 {error.validator_value}。", (field,), code="FIELD_TYPE"
        )
    if error.validator == "format":
        expected = (
            "HTTPS URL（含域名、无内嵌凭据和片段，端口为默认或443）"
            if error.validator_value == "pixverse-https-url"
            else "YYYY-MM-DD HH:MM:SS"
        )
        return InputError(f"字段 {field} 必须使用 {expected}。", (field,), code="FIELD_FORMAT")
    limits = {
        "minimum": "最小值",
        "maximum": "最大值",
        "minLength": "最小长度",
        "maxLength": "最大长度",
        "minItems": "最少数量",
        "maxItems": "最多数量",
    }
    if error.validator in limits:
        return InputError(
            f"字段 {field} 的{limits[error.validator]}为 {error.validator_value}。",
            (field,),
            code="FIELD_RANGE",
        )
    if error.validator == "additionalProperties":
        return InputError(
            f"字段 {field} 含当前工具协议未定义的参数；请使用声明中的公开字段。",
            (field,), code="UNKNOWN_FIELD",
            allowed_values=sorted(error.schema.get("properties", {})),
        )
    message = error.schema.get("description") or f"字段 {field} 不符合协议约束。"
    return InputError(message, (field,), code="FIELD_FORMAT")


def validate(validator, arguments):
    """实际执行与 tools/list 同一份协议，有限 JSON 数字属于基础协议要求。"""
    try:
        json.dumps(arguments, allow_nan=False)
    except (ValueError, TypeError):
        raise InputError("参数必须是合法 JSON，数值必须有限。", code="INVALID_JSON") from None
    errors = sorted(
        validator.iter_errors(arguments),
        key=lambda e: (e.validator in ("oneOf", "anyOf", "if"), tuple(map(str, e.absolute_path))),
    )
    if errors:
        raise _detail(errors[0])


def validators(schemas):
    """为全部工具编译公开协议，启用字段格式检查。"""
    return {
        name: Draft202012Validator(schema, format_checker=FORMATS)
        for name, schema in schemas.items()
    }


VALIDATORS = validators(SCHEMAS)


def json_object(raw):
    """解析 CLI JSON 对象，拒绝重复字段且不在错误中回显原始素材。"""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InputError("JSON 对象不允许重复字段。", code="INVALID_JSON")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique) if isinstance(raw, str) else raw
    except ValueError:
        raise InputError("参数必须是有效 JSON 对象。", code="INVALID_JSON") from None
    if not isinstance(value, dict):
        raise InputError("参数必须是 JSON 对象。", code="FIELD_TYPE")
    return value


def prepare_arguments(name, parameters):
    """将 CLI 语法映射到独立打包的公开契约；已解析素材仅读取一次。"""
    parameters = dict(parameters)
    if name in ("agent_ecommerce_native", "agent_ecommerce_template"):
        parameters["duration"] = int(parameters["duration"])
    if name in ("template_list", "voice_list"):
        parameters["page_size"] = int(parameters["page_size"])
    if name in ("image_upload", "media_upload"):
        if (parameters.get("file") is None) == (parameters.get("url") is None):
            raise InputError("--file 和 --url 必须且只能提供一个。", ("file", "url"),
                             code="FIELD_COMBINATION")
        if parameters.get("file") is not None:
            return parameters
    for key in ("image_ref", "video_ref", "frame", "raw_inputs"):
        if key in parameters:
            parameters[key] = tuple(json_object(raw) for raw in parameters[key])
    lyric_file = parameters.get("lyric_timestamp_file")
    if lyric_file is not None:
        try:
            parameters["lyric_timestamp_file"] = json_object(
                Path(lyric_file).read_text(encoding="utf-8")
            )
        except UnicodeError:
            raise InputError("歌词文件必须是 UTF-8 JSON。", ("lyric_timestamp",),
                             code="INVALID_JSON") from None
    aliases = {"creation_type": "creation_types", "credits_status": "credits_statuses",
               "template_id": "template_ids" if name == "template_list" else "template_id",
               "raw_inputs": "inputs", "frame": "frames", "image_ref": "image_references",
               "video_ref": "video_references", "lyric_timestamp_file": "lyric_timestamp"}
    if name in ("video_fusion", "video_modify", "template_generate",
                "agent_ecommerce_native", "agent_ecommerce_template"):
        aliases["img_id"] = "img_ids"
    if name == "video_modify":
        aliases.update(mask_id="mask_ids", mask_url="mask_urls")
    arguments = {}
    for key, value in parameters.items():
        if key == "file" or value is None or isinstance(value, tuple) and not value:
            continue
        arguments[aliases.get(key, key)] = list(value) if isinstance(value, tuple) else value
    validate(VALIDATORS[name], arguments)
    return parameters
