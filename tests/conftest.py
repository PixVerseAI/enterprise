import httpx
import pytest
from click.testing import CliRunner

from cli import cli as commands
from cli.client import PlatformClient


@pytest.fixture(autouse=True)
def isolated_credentials(monkeypatch):
    # 测试不加载用户配置；只使用明确的合成值。
    monkeypatch.setenv("PIXVERSE_REGION", "cn")
    monkeypatch.setenv("PIXVERSE_API_KEY", "synthetic-test-key")

    def forbid_network(*args, **kwargs):
        raise AssertionError("离线测试禁止真实网络。请使用 MockTransport。")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbid_network)


@pytest.fixture
def invoke(monkeypatch):
    def run(args, response=None, status=200):
        requests = []

        def handler(request):
            request.read()
            requests.append(request)
            return httpx.Response(
                status,
                json=response
                if response is not None
                else {
                    "ErrCode": 0,
                    "Resp": {"video_id": 123, "img_id": 456, "media_id": 789, "status": 5},
                },
            )

        def factory(config, **kwargs):
            return PlatformClient(config, transport=httpx.MockTransport(handler), **kwargs)

        monkeypatch.setattr(commands, "PlatformClient", factory)
        return CliRunner().invoke(commands.cli, args), requests

    return run
