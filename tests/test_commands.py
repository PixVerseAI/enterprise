import json

import pytest

from cli.config import PRODUCTION_URLS


@pytest.mark.parametrize("legacy", [None, "cn", "ov", "invalid"])
@pytest.mark.parametrize("region", [None, "global", "cn"])
def test_region_option_overrides_legacy_environment(legacy, region, invoke, monkeypatch):
    """默认请求走 global，旧环境变量不能覆盖默认或显式地区。"""
    if legacy is not None:
        monkeypatch.setenv("PIXVERSE_REGION", legacy)
    args = [] if region is None else ["--region", region]
    result, requests = invoke([*args, "--json", "account", "balance"])
    expected = region or "global"
    assert result.exit_code == 0, result.output
    assert str(requests[0].url) == PRODUCTION_URLS[expected] + "/openapi/v2/account/balance"
    assert json.loads(result.stdout)["region"] == expected


@pytest.mark.parametrize("region", ["ov", "GLOBAL", "test", "preview", "../cn"])
def test_invalid_region_stops_before_network(region, invoke):
    """非法根选项应由命令协议直接拒绝，不能触发任何 HTTP 请求。"""
    result, requests = invoke(["--region", region, "--json", "account", "balance"])
    assert result.exit_code == 2 and not requests
    assert "global" in result.output and "cn" in result.output


@pytest.mark.parametrize("region", ["cn", "global"])
def test_task_query_command_preserves_region(region, invoke):
    """创建返回的完整查询命令可以直接执行，并沿用创建时的地区。"""
    import shlex

    result, requests = invoke(["--json", "video", "generate", "--prompt", "a cat"],
                              region=region)
    assert result.exit_code == 0, result.output
    query = shlex.split(json.loads(result.stdout)["query_command"])
    assert query == ["pixverse-api", "--region", region, "--json", "video", "get", "--id", "123"]
    follow_up, queries = invoke(query[1:], response={"ErrCode": 0, "Resp": {"status": 5}})
    assert follow_up.exit_code == 0
    assert queries[0].url.host == requests[0].url.host
    assert queries[0].method == "GET" and queries[0].url.path.endswith("/video/result/123")


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize(
    "args,method,path",
    [
        (["account", "balance"], "GET", "/account/balance"),
        (["video", "generate", "--prompt", "a cat"], "POST", "/video/text/generate"),
        (
            ["video", "from-image", "--img-id", "12", "--prompt", "a cat"],
            "POST",
            "/video/img/generate",
        ),
        (["video", "get", "--id", "123"], "GET", "/video/result/123"),
    ],
)
def test_shared_command_routing(region, args, method, path, invoke, monkeypatch):
    result, requests = invoke(["--json", *args], region=region)
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    request = requests[0]
    assert request.method == method
    assert str(request.url) == PRODUCTION_URLS[region] + "/openapi/v2" + path
    assert request.headers["API-KEY"] == "synthetic-test-key"
    data = json.loads(result.stdout)
    assert data["ok"] and data["region"] == region
    assert data["environment"] == "production"
    if method == "POST":
        payload = json.loads(request.content)
        assert payload["prompt"] == "a cat" and payload["duration"] == 5
        assert "API-KEY" not in payload
        assert "generate_audio_switch" not in payload
        if "img" in path:
            assert payload["img_id"] == 12 and "aspect_ratio" not in payload
        else:
            assert payload["aspect_ratio"] == "16:9"
        assert data["submission"] == "accepted"


def test_generation_optional_fields_are_not_lost(invoke):
    result, requests = invoke(
        [
            "video",
            "generate",
            "--prompt",
            "test",
            "--seed",
            "0",
            "--no-audio",
            "--multi-clip",
            "--model",
            "v6-max",
            "--duration",
            "1",
            "--quality",
            "360p",
            "--aspect-ratio",
            "1:1",
        ]
    )
    assert result.exit_code == 0
    payload = json.loads(requests[0].content)
    assert payload == {
        "prompt": "test",
        "seed": 0,
        "generate_audio_switch": False,
        "generate_multi_clip_switch": True,
        "model": "v6-max",
        "duration": 1,
        "quality": "360p",
        "aspect_ratio": "1:1",
    }


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("kind,field", [("image", "image"), ("media", "file")])
@pytest.mark.parametrize("source", ["file", "url"])
def test_multipart_uploads(region, kind, field, source, invoke, tmp_path, monkeypatch):
    media_file = tmp_path / ("素材.png" if kind == "image" else "素材.wav")
    media_file.write_bytes(b"synthetic-upload-bytes")
    value = str(media_file) if source == "file" else "https://example.com/media"
    result, requests = invoke(["--json", kind, "upload", "--" + source, value], region=region)
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == PRODUCTION_URLS[region] + f"/openapi/v2/{kind}/upload"
    assert "multipart/form-data; boundary=" in request.headers["content-type"]
    expected = field if source == "file" else field + "_url"
    assert f'name="{expected}"'.encode() in request.content
    assert (b"synthetic-upload-bytes" if source == "file" else value.encode()) in request.content


@pytest.mark.parametrize(
    "args",
    [
        ["image", "upload"],
        ["media", "upload", "--file", "missing", "--url", "https://example.com/a"],
        ["image", "upload", "--file", "missing"],
        ["media", "upload", "--url", "ftp://example.com/file"],
        ["media", "upload", "--url", "https://user:password@example.com/file"],
        ["video", "generate", "--prompt", " "],
        ["video", "generate", "--prompt", "x" * 5001],
    ],
)
def test_invalid_inputs_do_not_send_requests(args, invoke):
    result, requests = invoke(["--json", *args])
    assert result.exit_code == 2 and not requests
    assert not result.stdout
    assert json.loads(result.stderr)["error"]["type"] == "validation"


@pytest.mark.parametrize(
    "status,name,exit_code",
    [
        (1, "completed", 0),
        (5, "generating", 0),
        (7, "moderation_failed", 1),
        (8, "failed", 1),
        (99, "unknown", 0),
    ],
)
def test_task_states(status, name, exit_code, invoke):
    result, requests = invoke(
        ["--json", "video", "get", "--id", "123"],
        {
            "ErrCode": 0,
            "Resp": {"status": status, "url": "https://example.com/result.mp4"},
        },
    )
    assert result.exit_code == exit_code
    data = json.loads(result.stdout)
    assert data["task_status"] == name and data["output_url_verified"] is False
    assert len(requests) == 1


def test_business_error_stderr_and_redaction(invoke):
    result, requests = invoke(
        ["--json", "account", "balance"],
        {
            "ErrCode": 100,
            "ErrMsg": "synthetic-test-key",
            "Error": {"Type": "API_KEY_INVALID"},
            "token": "do-not-print",
        },
    )
    assert result.exit_code == 1 and not result.stdout
    data = json.loads(result.stderr)
    assert data["error"]["response"]["Error"]["Type"] == "API_KEY_INVALID"
    assert "do-not-print" not in result.stderr and "synthetic-test-key" not in result.stderr
    assert len(requests) == 1
