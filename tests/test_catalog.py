"""用真实命令与离线HTTP验证账务、模板路由、输入边界及公共参数。"""

import json
import re
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from cli import cli as commands
from cli.client import PlatformClient
from cli.config import PRODUCTION_URLS
from cli.protocol import SCHEMAS

START = ["--start-time", "2026-11-01 00:00:00", "--end-time", "2026-11-02 00:00:00"]
STANDARD = ["--model", "v5.6", "--duration", "5", "--quality", "720p"]
STANDARD_META = {"type": 1, "template_id": 11, "template_mode": "standard", "effect_type": "1"}
WORKFLOW_META = {
    "type": 1,
    "template_id": 11,
    "template_mode": "workflow",
    "outputs": [{"content_type": "video"}],
    "input_limit": [{"input_key": "hero", "content_type": "image"}],
}


@pytest.fixture
def sequence(monkeypatch):
    """按实际请求顺序提供响应；意外额外请求会立即失败。"""

    def run(args, bodies, *, region="global"):
        requests = []

        def handler(request):
            request.read()
            requests.append(request)
            response = bodies[len(requests) - 1]
            if isinstance(response, Exception):
                raise response
            return httpx.Response(200, json=response)

        monkeypatch.setattr(
            commands,
            "PlatformClient",
            lambda config, **kw: PlatformClient(
                config,
                transport=httpx.MockTransport(handler),
                **kw,
            ),
        )
        result = CliRunner().invoke(commands.cli, ["--region", region, "--json", *args])
        return result, requests

    return run


def ok(resp):
    return {"ErrCode": 0, "Resp": resp}


def metadata(item):
    return ok({"effect_items": [item]})


@pytest.mark.parametrize("region", ["cn", "global"])
def test_usage_filters_and_key_scope(region, invoke, monkeypatch):
    result, requests = invoke(
        [
            "--json",
            "account",
            "usage",
            *START,
            "--limit",
            "100",
            "--creation-type",
            "agent",
            "--creation-type",
            "future_type",
            "--credits-status",
            "consume",
            "--credits-status",
            "refund",
        ],
        response=ok({"items": [], "next_cursor": "", "has_more": False}),
        region=region,
    )
    assert result.exit_code == 0, result.output
    assert len(requests) == 1 and requests[0].method == "POST"
    assert (
        str(requests[0].url) == PRODUCTION_URLS[region] + "/openapi/v2/account/billing/usage-detail"
    )
    assert json.loads(requests[0].content) == {
        "start_time": START[1],
        "end_time": START[3],
        "limit": 100,
        "creation_type": ["agent", "future_type"],
        "credits_status": ["consume", "refund"],
    }
    assert requests[0].headers["API-KEY"] == "synthetic-test-key"


def test_usage_cursor_is_opaque_and_not_automatically_followed(invoke):
    cursor = "opaque+/=="
    result, requests = invoke(
        ["--json", "account", "usage", "--cursor", cursor],
        response=ok(
            {
                "items": [{"credits_status": "refund", "credits": 5}],
                "next_cursor": "next-page",
                "has_more": True,
            }
        ),
    )
    assert result.exit_code == 0 and len(requests) == 1
    assert json.loads(requests[0].content) == {"cursor": cursor}
    assert json.loads(result.stdout)["response"]["Resp"]["has_more"] is True


@pytest.mark.parametrize(
    "args",
    [
        [],
        START[:2],
        [*START, "--limit", "0"],
        ["--start-time", "2026-02-30 00:00:00", "--end-time", "2026-03-01 00:00:00"],
        [*START, "--cursor", "opaque"],
        ["--cursor", "opaque", "--limit", "10"],
    ],
)
def test_usage_invalid_before_network(args, invoke):
    result, requests = invoke(["--json", "account", "usage", *args])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize(
    "body",
    [
        {"items": [], "has_more": 1, "next_cursor": ""},
        {"items": None, "has_more": False, "next_cursor": ""},
        {"items": [], "has_more": False},
    ],
)
def test_usage_protocol_errors_keep_trace(body, invoke):
    result, _ = invoke(["--json", "account", "usage", *START], response=ok(body))
    error = json.loads(result.stderr)["error"]
    assert result.exit_code == 1 and error["type"] == "protocol" and error["trace_id"]


@pytest.mark.parametrize("region", ["cn", "global"])
def test_template_list_filters(region, invoke, monkeypatch):
    result, requests = invoke(
        [
            "--json",
            "template",
            "list",
            "--mode",
            "workflow",
            "--template-id",
            "12",
            "--template-id",
            "11",
            "--page",
            "2",
            "--page-size",
            "20",
        ],
        response=ok({"effect_items": []}),
        region=region,
    )
    assert result.exit_code == 0 and len(requests) == 1
    assert requests[0].url.host == (
        "app-api.pixverseai.cn" if region == "cn" else "app-api.pixverse.ai"
    )
    assert dict(requests[0].url.params) == {
        "type": "1",
        "page": "2",
        "pageSize": "20",
        "template_mode": "workflow",
        "template_ids": "12,11",
    }


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize(
    "images,effect_type,field,expected",
    [
        ([21], "1", "img_id", 21),
        ([22, 21], "2", "img_ids", [22, 21]),
        ([21], "2", "img_ids", [21]),
        ([], "1", "aspect_ratio", "9:16"),
    ],
)
def test_standard_template_metadata_then_single_write(
    region,
    images,
    effect_type,
    field,
    expected,
    sequence,
    monkeypatch,
):
    args = [
        "template",
        "generate",
        "--id",
        "11",
        *STANDARD,
        "--seed",
        "0",
        "--no-audio",
        "--webhook-id",
        "31",
        "--negative-prompt",
        "blur",
    ]
    for image in images:
        args += ["--img-id", str(image)]
    if not images:
        args += ["--prompt", "a cat", "--aspect-ratio", "9:16"]
    result, requests = sequence(
        args,
        [
            metadata({**STANDARD_META, "effect_type": effect_type}),
            ok({"video_id": 123}),
        ],
        region=region,
    )
    assert result.exit_code == 0, result.output
    assert [r.method for r in requests] == ["GET", "POST"]
    assert all(str(r.url).startswith(PRODUCTION_URLS[region]) for r in requests)
    body = json.loads(requests[1].content)
    assert body[field] == expected and body["template_id"] == 11
    assert body["seed"] == 0 and body["generate_audio_switch"] is False
    assert body["webhook_id"] == "31" and body["negative_prompt"] == "blur"
    assert requests[1].url.path.endswith(
        "/video/img/generate" if images else "/video/text/generate"
    )
    assert json.loads(result.stdout)["discovery_trace_id"] != json.loads(result.stdout)["trace_id"]


@pytest.mark.parametrize("region", ["cn", "global"])
def test_workflow_typed_inputs_and_default_text(region, sequence, monkeypatch):
    inputs = [
        {"input_key": "hero", "img_id": 21},
        {"input_key": "sound", "audio_media_id": 41},
        {"input_key": "clip", "source_video_id": 51},
    ]
    fields = WORKFLOW_META["input_limit"] + [
        {"input_key": "sound", "content_type": "audio"},
        {"input_key": "clip", "content_type": "video"},
        {"input_key": "copy", "content_type": "text", "text": "default"},
    ]
    args = ["template", "generate", "--id", "11"]
    for item in inputs:
        args += ["--input", json.dumps(item)]
    result, requests = sequence(
        args,
        [
            metadata({**WORKFLOW_META, "input_limit": fields}),
            ok({"task_id": 456, "status": 5}),
        ],
        region=region,
    )
    assert result.exit_code == 0, result.output
    assert len(requests) == 2 and requests[1].url.path == "/openapi/v2/template/generate"
    assert json.loads(requests[1].content) == {"template_id": 11, "inputs": inputs}
    body = json.loads(result.stdout)
    assert body["submission"] == "accepted" and body["query_command"] == (
        f"pixverse-api --region {region} --json template get --id 456"
    )


@pytest.mark.parametrize(
    "raw",
    [
        "[]",
        "not-json",
        '{"input_key":"hero","img_id":true}',
        '{"input_key":"hero","img_id":"21"}',
        '{"input_key":"hero","img_id":0}',
        '{"input_key":"hero","img_id":18446744073709551616}',
        '{"input_key":"hero","img_id":21,"audio_media_id":41}',
        '{"input_key":"hero","img_id":21,"img_id":22}',
        '{"input_key":"hero","unexpected":21}',
    ],
)
def test_bad_workflow_json_before_discovery(raw, sequence):
    result, requests = sequence(["template", "generate", "--id", "11", "--input", raw], [])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize(
    "item,extra",
    [
        ({**WORKFLOW_META, "outputs": [{"content_type": "image"}]}, []),
        ({**WORKFLOW_META, "outputs": [{"content_type": "video"}, {"content_type": "image"}]}, []),
        ({**WORKFLOW_META, "type": 2}, []),
        (WORKFLOW_META, ["--input", '{"input_key":"hero","img_id":21}', "--no-audio"]),
        (STANDARD_META, ["--img-id", "21"]),
    ],
)
def test_incompatible_templates_never_submit(item, extra, sequence):
    result, requests = sequence(["template", "generate", "--id", "11", *extra], [metadata(item)])
    assert result.exit_code in (1, 2) and len(requests) == 1
    assert requests[0].method == "GET"


@pytest.mark.parametrize(
    "state,exit_code,name",
    [
        (1, 0, "completed"),
        ("succeeded", 0, "completed"),
        (5, 0, "generating"),
        ("running", 0, "generating"),
        ("pending", 0, "generating"),
        ("queued", 0, "generating"),
        (7, 1, "moderation_failed"),
        (8, 1, "failed"),
        ("failed", 1, "failed"),
        ("canceled", 1, "failed"),
        ("cancelled", 1, "failed"),
        (99, 0, "unknown"),
        ("1", 0, "unknown"),
    ],
)
def test_workflow_result_state_and_final_urls(state, exit_code, name, invoke):
    """完成状态统一返回最终链接，生成中、失败和未知状态不返回成片。"""
    result, requests = invoke(
        ["--json", "template", "get", "--id", "456"],
        response=ok(
            {
                "task_id": 456,
                "status": state,
                "contents": [
                    {"content_type": "video", "status": 1, "url": "https://example.com/final1.mp4"},
                    {
                        "content_type": "video",
                        "status": 5,
                        "url": "https://example.com/intermediate.mp4",
                    },
                ],
            }
        ),
    )
    assert result.exit_code == exit_code, result.output
    body = json.loads(result.stdout)
    assert body["task_status"] == name and body["output_url_verified"] is False
    completed = name == "completed"
    assert body["output_urls"] == (["https://example.com/final1.mp4"] if completed else [])
    assert body["output_url"] == ("https://example.com/final1.mp4" if completed else None)
    assert len(requests) == 1 and requests[0].url.path == "/openapi/v2/template/result/456"


@pytest.mark.parametrize("state", [1, "succeeded"])
@pytest.mark.parametrize("count", [0, 2])
def test_workflow_completed_urls_preserve_empty_and_multiple_outputs(state, count, invoke):
    """保留全部完成视频，多成片时不猜测一个主链接，也不混入中间或图片产物。"""
    urls = [f"https://example.com/final{i}.mp4" for i in range(count)]
    contents = [{"content_type": "video", "status": 1, "url": url} for url in urls]
    contents.extend([
        {"content_type": "video", "status": 5, "url": "https://example.com/intermediate.mp4"},
        {"content_type": "image", "status": 1, "url": "https://example.com/image.png"},
    ])
    result, requests = invoke(
        ["--json", "template", "get", "--id", "456"],
        response=ok({"task_id": 456, "status": state, "contents": contents}),
    )
    body = json.loads(result.stdout)
    assert result.exit_code == 0 and len(requests) == 1
    assert body["task_status"] == "completed" and body["output_urls"] == urls
    assert body["output_url"] is None and body["output_url_verified"] is False


@pytest.mark.parametrize(
    "response",
    [
        ok({}),
        ok({"task_id": True}),
        {"ErrCode": 500070, "ErrMsg": "not enabled"},
        httpx.ReadTimeout("simulated"),
    ],
)
def test_template_write_failure_never_falls_back_or_retries(response, sequence):
    result, requests = sequence(
        ["template", "generate", "--id", "11", *STANDARD, "--img-id", "21"],
        [metadata(STANDARD_META), response],
    )
    assert result.exit_code == 1 and len(requests) == 2
    assert json.loads(result.stderr)["error"]["trace_id"]


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("image", [False, True])
def test_base_generation_webhook_and_negative_prompt(region, image, invoke, monkeypatch):
    args = ["video", "from-image", "--img-id", "21"] if image else ["video", "generate"]
    result, requests = invoke(
        [
            "--json",
            *args,
            "--prompt",
            "test",
            "--negative-prompt",
            "blur",
            "--webhook-id",
            "31",
            "--no-audio",
            "--seed",
            "0",
        ],
        region=region,
    )
    assert result.exit_code == 0, result.output
    body = json.loads(requests[0].content)
    assert body["webhook_id"] == "31" and body["negative_prompt"] == "blur"
    assert body["seed"] == 0 and body["generate_audio_switch"] is False


@pytest.mark.parametrize(
    "extra", [["--webhook-id", "0"], ["--webhook-id", "abc"]]
)
def test_invalid_shared_generation_options_before_network(extra, invoke):
    result, requests = invoke(["video", "generate", "--prompt", "test", *extra])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize("item,extra", [
    (WORKFLOW_META, []),
    (WORKFLOW_META, ["--input", '{"input_key":"unknown","img_id":21}']),
    (WORKFLOW_META, ["--input", '{"input_key":"hero","text":"test"}']),
    (STANDARD_META, [*STANDARD, "--img-id", "21", "--img-id", "22"]),
    (STANDARD_META, [*STANDARD, "--img-id", "21", "--aspect-ratio", "1:1"]),
])
def test_template_dynamic_inputs_are_forwarded_once(item, extra, sequence):
    result, requests = sequence(["template", "generate", "--id", "11", *extra], [
        metadata(item), {"ErrCode": 4001, "ErrMsg": "Platform template rule"},
    ])
    data = json.loads(result.stderr)
    assert result.exit_code == 1 and len(requests) == 2
    assert requests[0].method == "GET" and requests[1].method == "POST"
    assert data["stage"] == "upstream" and data["submission_state"] == "rejected"


def test_template_discovery_failure_does_not_claim_submission(sequence):
    result, requests = sequence(["template", "generate", "--id", "11"], [metadata(STANDARD_META)])
    data = json.loads(result.stderr)
    assert result.exit_code == 2 and len(requests) == 1
    assert data["stage"] == "discovery" and data["submission_state"] == "not_submitted"
    assert data["error"]["trace_id"] == requests[0].headers["Ai-trace-id"]


def test_template_read_failure_is_not_a_write_failure(sequence):
    result, requests = sequence(["template", "generate", "--id", "11"], [
        {"ErrCode": 4001, "ErrMsg": "Template unavailable"},
    ])
    assert result.exit_code == 1 and len(requests) == 1
    data = json.loads(result.stderr)
    assert data["stage"] == "discovery" and data["submission_state"] == "not_submitted"


def test_avatar_guides_qualities_match_input_contract():
    """首页可精简，迁移后的CLI/MCP指南仍须覆盖当前Avatar清晰度。"""
    root = Path(__file__).resolve().parents[1]
    expected = set(SCHEMAS["video_avatar"]["properties"]["quality"]["enum"])
    for name in ("cli", "mcp"):
        guide = re.search(r"Avatar (?:accepts|supports) ([0-9p/]+)",
                          (root / "docs" / f"{name}.md").read_text())
        assert guide is not None
        assert set(guide.group(1).split("/")) == expected
        for readme in ("README.md", "README.zh-CN.md"):
            assert f"](docs/{name}.md)" in (root / readme).read_text()
