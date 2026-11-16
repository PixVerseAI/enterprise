import json
from uuid import UUID

import httpx
import pytest

from cli.client import APIError, PlatformClient, redact
from cli.config import PRODUCTION_URLS, Config, ConfigurationError


@pytest.mark.parametrize("region", ["cn", "global"])
def test_production_routing_and_unique_trace(region):
    traces = []

    def handler(request):
        assert str(request.url) == PRODUCTION_URLS[region] + "/openapi/v2/account/balance"
        assert request.headers["API-KEY"] == "synthetic-test-key"
        traces.append(request.headers["Ai-trace-id"])
        assert UUID(traces[-1]).version == 4
        return httpx.Response(200, json={"ErrCode": 0, "Resp": {"credit_package": 12}})

    with PlatformClient(
        Config(region, "synthetic-test-key"), transport=httpx.MockTransport(handler)
    ) as c:
        assert c.balance()["response"]["Resp"]["credit_package"] == 12
        c.balance()
    assert len(set(traces)) == 2


@pytest.mark.parametrize("region", ["", "ov", "us", "CN", "test", "../global"])
def test_explicit_region_is_strict(region):
    """地区参数只接受公开的两个取值，不能切换到其他环境。"""
    with pytest.raises(ConfigurationError, match="--region"):
        Config.from_env(region=region)


@pytest.mark.parametrize("legacy", ["cn", "ov", "invalid"])
def test_legacy_region_environment_is_ignored(legacy, monkeypatch):
    """历史地区环境变量不能覆盖默认值或显式选择。"""
    monkeypatch.setenv("PIXVERSE_REGION", legacy)
    assert Config.from_env().region == "global"
    assert Config.from_env().base_url == "https://app-api.pixverse.ai"
    assert Config.from_env(region="cn").base_url == "https://app-api.pixverseai.cn"


@pytest.mark.parametrize("key", ["", " ", "a b", "a\nb", "中文"])
def test_key_validation(key, monkeypatch):
    monkeypatch.setenv("PIXVERSE_API_KEY", key)
    with pytest.raises(ConfigurationError, match="PIXVERSE_API_KEY"):
        Config.from_env()


def test_no_configuration_fallback(monkeypatch):
    monkeypatch.delenv("PIXVERSE_API_KEY")
    monkeypatch.setenv("PIX_CN_OPENAPI_API_KEY_PROD", "synthetic-legacy")
    with pytest.raises(ConfigurationError):
        Config.from_env()
    assert "synthetic-test-key" not in repr(Config("cn", "synthetic-test-key"))


@pytest.mark.parametrize(
    "status,body,kind",
    [
        (401, {"ErrCode": 1}, "http"),
        (429, {"ErrCode": 1}, "http"),
        (500, {"ErrCode": 1}, "http"),
        (
            200,
            {"ErrCode": 12, "ErrMsg": "denied", "Error": {"Type": "API_KEY_INVALID"}},
            "business",
        ),
        (200, {}, "protocol"),
        (200, {"ErrCode": "0", "Resp": {}}, "protocol"),
        (200, {"ErrCode": False, "Resp": {}}, "protocol"),
        (200, {"ErrCode": 0, "Resp": None}, "protocol"),
        (200, [], "protocol"),
    ],
)
def test_http_business_and_protocol_errors(status, body, kind):
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    with PlatformClient(Config.from_env(), transport=transport) as c:
        with pytest.raises(APIError) as caught:
            c.balance()
    assert caught.value.kind == kind
    assert caught.value.http_status == status
    assert caught.value.response == body


def test_non_json_error_does_not_echo_html():
    transport = httpx.MockTransport(lambda _: httpx.Response(502, text="private-upstream-data"))
    with PlatformClient(Config.from_env(), transport=transport) as c:
        with pytest.raises(APIError) as caught:
            c.balance()
    assert caught.value.response is None
    assert "private-upstream-data" not in str(caught.value)


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_generation_network_error_never_retries(error):
    requests = []

    def handler(request):
        requests.append(request)
        raise error("synthetic-test-key must not be echoed", request=request)

    with PlatformClient(Config.from_env(), transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(APIError) as caught:
            c.generate({"prompt": "example"})
    assert len(requests) == 1
    assert "synthetic-test-key" not in str(caught.value)


def test_redirect_never_forwards_credentials():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(307, headers={"location": "https://example.com/steal"})

    with PlatformClient(Config.from_env(), transport=httpx.MockTransport(handler)) as c:
        with pytest.raises(APIError, match="HTTP"):
            c.balance()
    assert len(requests) == 1


def test_recursive_redaction():
    data = {
        "API-KEY": "secret",
        "nested": [{"access_token": "secret"}, {"WebhookSecret": "secret"}],
        "message": "synthetic-test-key",
        "url": "https://example.com/?token=secret&x=1",
    }
    cleaned = redact(data, "synthetic-test-key")
    encoded = json.dumps(cleaned)
    assert "secret" not in encoded and "synthetic-test-key" not in encoded
    assert "[REDACTED]" in encoded


def test_generation_requires_video_id():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"ErrCode": 0, "Resp": {}}))
    with PlatformClient(Config.from_env(), transport=transport) as c:
        with pytest.raises(APIError, match="video_id"):
            c.generate({})


@pytest.mark.parametrize("status", [None, [], {}, True])
def test_task_rejects_malformed_status(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"ErrCode": 0, "Resp": {"status": status}})
    )
    with PlatformClient(Config.from_env(), transport=transport) as c:
        with pytest.raises(APIError, match="status"):
            c.task(123)
