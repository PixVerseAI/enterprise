"""自定义音色的公开契约与删除空响应兼容，不访问生产。"""

import json

import httpx
import pytest

from cli.client import APIError, PlatformClient
from cli.config import PRODUCTION_URLS, Config

CUSTOM = "custom_0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize("region", ["cn", "global"])
def test_create_custom_voice(region, invoke, monkeypatch):
    result, requests = invoke(
        ["--json", "voice", "create", "--name", " 临时测试音色 ", "--audio-media-id", "41"],
        response={"ErrCode": 0, "Resp": {"speaker_id": CUSTOM}},
        region=region,
    )
    assert result.exit_code == 0 and len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == PRODUCTION_URLS[region] + "/openapi/v2/video/tts_speaker"
    assert json.loads(requests[0].content) == {"name": " 临时测试音色 ", "audio_media_id": 41}
    assert json.loads(result.stdout)["speaker_id"] == CUSTOM
    assert "submission" not in json.loads(result.stdout)


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("speaker_type", ["system", "custom", "all"])
def test_new_voice_list(region, speaker_type, invoke, monkeypatch):
    response = {
        "ErrCode": 0,
        "Resp": {
            "total": 1,
            "data": [
                {
                    "speaker_id": CUSTOM,
                    "speaker_type": "custom",
                    "audio_url": "https://example.com/sample.wav",
                }
            ],
        },
    }
    result, requests = invoke(
        [
            "--json",
            "voice",
            "list",
            "--type",
            speaker_type,
            "--scene",
            "avatar",
            "--page-size",
            "20",
        ],
        response=response,
        region=region,
    )
    assert result.exit_code == 0 and len(requests) == 1
    assert requests[0].url.path == "/openapi/v2/video/tts_speaker"
    assert dict(requests[0].url.params) == {
        "speaker_type": speaker_type,
        "scene": "avatar",
        "page_num": "1",
        "page_size": "20",
    }
    assert json.loads(result.stdout)["response"]["Resp"]["data"][0]["audio_url"]


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("resp", [None, {}])
def test_delete_custom_voice_accepts_documented_empty_response(region, resp, invoke, monkeypatch):
    result, requests = invoke(
        ["--json", "voice", "delete", "--speaker-id", CUSTOM],
        response={"ErrCode": 0, "Resp": resp},
        region=region,
    )
    assert result.exit_code == 0 and len(requests) == 1
    assert requests[0].method == "DELETE"
    assert requests[0].url.path == "/openapi/v2/video/tts_speaker/" + CUSTOM
    assert not requests[0].content and json.loads(result.stdout)["response"]["Resp"] == resp


@pytest.mark.parametrize(
    "args",
    [
        ["delete", "--speaker-id", "1"],
        ["create", "--name", " ", "--audio-media-id", "41"],
        ["create", "--name", "名" * 129, "--audio-media-id", "41"],
        ["create", "--name", "test", "--audio-media-id", "0"],
        ["list", "--type", "custom", "--page-size", "7"],
    ],
)
def test_voice_invalid_inputs_before_network(args, invoke):
    result, requests = invoke(["--json", "voice", *args])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize("resp", [{}, {"speaker_id": ""}, {"speaker_id": True}])
def test_create_missing_custom_id_keeps_trace_without_retry(resp, invoke):
    result, requests = invoke(
        ["--json", "voice", "create", "--name", "test", "--audio-media-id", "41"],
        response={"ErrCode": 0, "Resp": resp},
    )
    assert result.exit_code == 1 and len(requests) == 1
    error = json.loads(result.stderr)["error"]
    assert error["type"] == "protocol" and error["trace_id"]


@pytest.mark.parametrize(
    "body,allow",
    [
        ({"ErrCode": 0, "Resp": None}, False),
        ({"ErrCode": 0}, True),
        ({"ErrCode": 0, "Resp": []}, True),
    ],
)
def test_empty_response_opt_in_does_not_weaken_other_protocols(body, allow):
    with PlatformClient(
        Config("cn", "synthetic-test-key"),
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json=body),
        ),
    ) as client:
        with pytest.raises(APIError) as error:
            client.request(
                "DELETE", "/openapi/v2/video/tts_speaker/" + CUSTOM, allow_empty_resp=allow
            )
    assert error.value.kind == "protocol"


def test_mv_stays_v3_custom_only(invoke):
    result, requests = invoke(
        ["--json", "agent", "mv", "--audio-media-id", "41", "--mv-agent-type", "vibe_mv_beat_mix"]
    )
    assert result.exit_code == 2 and not requests
