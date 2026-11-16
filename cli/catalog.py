"""用量与视频模板公开接口；国内海外共享逻辑，按模板元数据路由。"""

import click

from .client import APIError
from .protocol import json_object
from .workflows import ID, QUALITIES, RATIOS, SEED, compact, text, webhook

TEMPLATE_LIST = "/openapi/v2/video/effects/templates/list"


def protocol_error(result, message):
    """协议错误保留实际请求的TraceId和原始脱敏响应。"""
    raise APIError(
        "protocol",
        message,
        trace_id=result["trace_id"],
        http_status=result["http_status"],
        response=result["response"],
    )


def usage_payload(start_time, end_time, creation_type, credits_status, limit, cursor):
    """保留不透明游标和原始日期；窗口及排序等业务规则由 Platform 校验。"""
    if cursor:
        return {"cursor": cursor}
    return {
        "start_time": start_time,
        "end_time": end_time,
        "limit": limit or 50,
        "creation_type": list(creation_type),
        "credits_status": list(credits_status),
    }


def template_list(client, template_id=(), mode=None, page=1, page_size=50):
    """只发现视频模板，保留元数据和实际地域可用性。"""
    params = {"type": 1, "page": page, "pageSize": page_size}
    if template_id:
        params["template_ids"] = ",".join(map(str, template_id))
    if mode:
        params["template_mode"] = mode
    result = client.request("GET", TEMPLATE_LIST, params=params)
    items = result["response"]["Resp"].get("effect_items")
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        protocol_error(result, "模板响应缺少有效的effect_items。")
    if any(type(item.get("type")) is not int or item["type"] != 1 for item in items):
        protocol_error(result, "模板列表包含非视频或无法识别的模板类型。")
    return result


def find_template(client, template_id):
    """精确查找当前地区的公开视频模板，避免盲提交未知或图片模板。"""
    result = template_list(client, (template_id,))
    matches = [
        item
        for item in result["response"]["Resp"]["effect_items"]
        if str(item.get("template_id")) == str(template_id)
    ]
    if len(matches) != 1:
        raise ValueError("当前地区未找到唯一可用的视频模板，请先调用template list。")
    item = matches[0]
    mode = item.get("template_mode")
    if mode not in ("standard", "workflow"):
        protocol_error(result, "模板响应缺少有效的template_mode。")
    if mode == "workflow":
        outputs = item.get("outputs")
        if (
            not isinstance(outputs, list)
            or not outputs
            or any(
                not isinstance(out, dict) or out.get("content_type") != "video" for out in outputs
            )
        ):
            raise ValueError("本CLI仅生成纯视频输出模板；图片或混合输出不在当前范围。")
    return item, result["trace_id"]


def parse_inputs(values):
    """只解析公开结构；模板 input_key、数量及必填性由 Platform 校验。"""
    return [json_object(raw) for raw in values]


def standard_payload(template, template_id, img_id, options):
    """传统模板复用视频生成协议，单图和多图保留不同字段。"""
    model, duration, quality = (options[k] for k in ("model", "duration", "quality"))
    if model in (None, "") or duration is None or quality is None:
        raise ValueError("传统模板必须指定--model、--duration和--quality。")
    single = str(template.get("effect_type")) == "1"
    if not template.get("effect_type"):
        raise ValueError("模板缺少effect_type，无法选择单图或多图协议。")
    endpoint = "img" if img_id or not single else "text"
    if endpoint == "text":
        text(options["prompt"], "prompt")
    payload = {
        "template_id": template_id,
        **compact(
            {
                "model": model,
                "duration": duration,
                "quality": quality,
                "prompt": options["prompt"],
                "negative_prompt": options["negative_prompt"],
                "seed": options["seed"],
                "generate_audio_switch": options["audio"],
                "aspect_ratio": options["aspect_ratio"],
            }
        ),
        **webhook(options["webhook_id"]),
    }
    if endpoint == "img":
        payload.update({"img_id": img_id[0]} if single and len(img_id) == 1
                       else {"img_ids": list(img_id)})
    else:
        payload["aspect_ratio"] = options["aspect_ratio"] or "16:9"
    return f"video/{endpoint}/generate", payload


def generate_template(client, template_id, img_id, raw_inputs, options):
    """先发现元数据再单次写入；不在失败后猜测其他入口或重复提交。"""
    inputs = parse_inputs(raw_inputs)
    template, discovery_trace_id = find_template(client, template_id)
    if template["template_mode"] == "standard":
        if raw_inputs:
            raise ValueError("传统模板使用--img-id/--prompt，不接受--input。")
        endpoint, payload = standard_payload(template, template_id, img_id, options)
        result = client.submit(endpoint, payload)
    else:
        if img_id or any(value is not None for value in options.values()):
            raise ValueError("Workflow模板只接受--input，不接受传统模板生成参数。")
        result = client.request(
            "POST",
            "/openapi/v2/template/generate",
            json={
                "template_id": template_id,
                "inputs": inputs,
            },
        )
        task_id = result["response"]["Resp"].get("task_id")
        if type(task_id) is not int or not 0 < task_id < 2**64:
            protocol_error(result, "模板创建响应缺少有效task_id，请核查后再决定是否重试。")
        result.update(submission="accepted", query_command=f"template get --id {task_id}")
    result["discovery_trace_id"] = discovery_trace_id
    return result


def workflow_result(client, task_id):
    """查询Workflow父任务与全部视频成片，失败终态沿用统一退出码。"""
    result = client.request("GET", f"/openapi/v2/template/result/{task_id}")
    body = result["response"]["Resp"]
    status, contents = body.get("status"), body.get("contents")
    if (
        type(status) not in (int, str)
        or not isinstance(contents, list)
        or any(not isinstance(item, dict) for item in contents)
    ):
        protocol_error(result, "Workflow响应缺少有效status或contents。")
    result["task_status"] = {
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
    }.get(status, "unknown")
    urls = [
        item["url"]
        for item in contents
        if item.get("content_type") == "video"
        and type(item.get("status")) is int
        and item.get("status") == 1
        and isinstance(item.get("url"), str)
        and item["url"]
    ]
    completed = result["task_status"] == "completed"
    result["output_urls"] = urls if completed else []
    result["output_url"] = urls[0] if completed and len(urls) == 1 else None
    result["output_url_verified"] = False
    return result


def register_catalog(root, account, action):
    """注册Key级用量与视频模板命令，共用既有鉴权和错误出口。"""

    @account.command("usage")
    @click.option("--start-time", help="YYYY-MM-DD HH:MM:SS；国内UTC+8，海外UTC。")
    @click.option("--end-time", help="排他结束时间；时间窗口规则由 Platform 校验。")
    @click.option("--creation-type", multiple=True, help="重复传业务类型；可扩展值由服务端校验。")
    @click.option("--credits-status", multiple=True, type=click.Choice(["consume", "refund"]))
    @click.option("--limit", type=click.IntRange(1, 100), help="首次查询每页条数，默认50。")
    @click.option("--cursor", help="原样传上一页next_cursor，不混用其他筛选。")
    @action
    def usage(client, **kwargs):
        """查询当前API Key的消耗/返还明细；每次只查询一页。"""
        payload = usage_payload(**kwargs)
        result = client.request("POST", "/openapi/v2/account/billing/usage-detail", json=payload)
        body = result["response"]["Resp"]
        if (
            not isinstance(body.get("items"), list)
            or type(body.get("has_more")) is not bool
            or (not isinstance(body.get("next_cursor"), str))
        ):
            protocol_error(result, "用量响应缺少有效items、has_more或next_cursor。")
        return result

    register_templates(root, action)


def register_templates(root, action):
    """将视频模板发现、元数据驱动提交和Workflow查询组织为单独命令组。"""

    @root.group("template")
    def template_group():
        """视频特效模板；按元数据区分standard与workflow。"""

    @template_group.command("list")
    @click.option("--template-id", type=ID, multiple=True)
    @click.option("--mode", type=click.Choice(["standard", "workflow"]))
    @click.option("--page", type=click.IntRange(1), default=1)
    @click.option("--page-size", type=click.Choice(["10", "20", "50", "100"]), default="50")
    @action
    def list_templates(client, page_size, **kwargs):
        """查询公开视频模板及其输入、时长、清晰度和价格元数据。"""
        return template_list(client, page_size=int(page_size), **kwargs)

    @template_group.command("get")
    @click.option("--id", "task_id", type=ID, required=True)
    @action
    def get_template(client, task_id):
        """查询Workflow task_id；传统模板video_id使用video get。"""
        return workflow_result(client, task_id)

    register_template_generate(template_group, action)


def register_template_generate(group, action):
    """传统模板与Workflow使用各自参数，不开放任意请求JSON透传。"""

    @group.command("generate")
    @click.option("--id", "template_id", type=ID, required=True)
    @click.option("--img-id", type=ID, multiple=True, help="传统模板图片；多图按顺序重复。")
    @click.option("--input", "raw_inputs", multiple=True, help="Workflow具名输入JSON对象。")
    @click.option("--model", help="传统模板必填；组合由服务端最终校验。")
    @click.option("--duration", type=click.IntRange(1), help="传统模板必填。")
    @click.option("--quality", type=click.Choice(QUALITIES), help="传统模板必填。")
    @click.option("--prompt")
    @click.option("--negative-prompt")
    @click.option("--aspect-ratio", type=click.Choice(RATIOS))
    @click.option("--seed", type=SEED)
    @click.option("--audio/--no-audio", default=None)
    @click.option("--webhook-id")
    @action
    def create_template(client, template_id, img_id, raw_inputs, **kwargs):
        """读取所选模板元数据后单次提交；图片/混合输出模板不接入。"""
        return generate_template(client, template_id, img_id, raw_inputs, kwargs)
