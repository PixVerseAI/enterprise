import json

import pytest

from cli.config import PRODUCTION_URLS


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("keep", [True, False])
def test_sound_effect_request_and_original_sound(invoke, monkeypatch, region, keep):
    """真实请求构造保留原声开关、零seed和同账号Webhook。"""
    result, requests = invoke(
        [
            "--json",
            "video",
            "sound-effect",
            "--video-media-id",
            "22",
            "--sound-effect-content",
            "rain",
            "--original-sound" if keep else "--no-original-sound",
            "--seed",
            "0",
            "--webhook-id",
            "33",
        ],
        region=region,
    )
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    assert (
        str(requests[0].url) == PRODUCTION_URLS[region] + "/openapi/v2/video/sound_effect/generate"
    )
    assert json.loads(requests[0].content) == {
        "video_media_id": 22,
        "sound_effect_content": "rain",
        "original_sound_switch": keep,
        "seed": 0,
        "webhook_id": "33",
    }
    assert json.loads(result.stdout)["submission"] == "accepted"


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("last", [{"img_id": 13}, {"img_id": 13, "duration": 0}])
def test_multi_transition_order_and_last_frame(invoke, monkeypatch, region, last):
    """两地提交保持帧顺序、分段提示词和末帧duration原语义。"""
    frames = [
        {"img_id": 12, "duration": 3, "prompt": "morning"},
        {"img_id": 11, "duration": 5, "prompt": "night"},
        last,
    ]
    args = ["--json", "video", "multi-transition", "--seed", "0", "--webhook-id", "33"]
    for frame in frames:
        args += ["--frame", json.dumps(frame)]
    result, requests = invoke(args, region=region)
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    assert (
        str(requests[0].url)
        == PRODUCTION_URLS[region] + "/openapi/v2/video/multi_transition/generate"
    )
    assert json.loads(requests[0].content) == {
        "multi_transition": frames,
        "model": "v5",
        "quality": "720p",
        "motion_mode": "normal",
        "seed": 0,
        "webhook_id": "33",
    }


@pytest.mark.parametrize("duration", [1, 8])
def test_multi_transition_two_frame_duration_boundaries(invoke, duration):
    """两帧分段边界1秒和8秒都应进入服务端校验。"""
    frames = [{"img_id": 11, "duration": duration}, {"img_id": 12, "duration": 0}]
    result, requests = invoke(
        [
            "video",
            "multi-transition",
            "--frame",
            json.dumps(frames[0]),
            "--frame",
            json.dumps(frames[1]),
        ]
    )
    assert result.exit_code == 0
    assert json.loads(requests[0].content)["multi_transition"] == frames


def test_sound_effect_automatic_content_from_generated_video(invoke):
    """自动音效允许省略内容和原声开关，并保持生成视频来源字段。"""
    result, requests = invoke(["video", "sound-effect", "--source-video-id", "21"])
    assert result.exit_code == 0
    assert json.loads(requests[0].content) == {"source_video_id": 21}


@pytest.mark.parametrize(
    "frames",
    [
        ['{"img_id":11}'],
        ["bad", '{"img_id":12}'],
        ["[]", '{"img_id":12}'],
        ['{"img_id":true,"duration":5}', '{"img_id":12}'],
        ['{"img_id":"11","duration":5}', '{"img_id":12}'],
        ['{"img_id":0,"duration":5}', '{"img_id":12}'],
        ['{"img_id":11,"duration":5,"token":"x"}', '{"img_id":12}'],
        ['{"img_id":11,"duration":true}', '{"img_id":12}'],
        ['{"img_id":11,"duration":1.5}', '{"img_id":12}'],
        ['{"img_id":11,"duration":5}', '{"img_id":12,"duration":false}'],
        ['{"img_id":11,"duration":5,"prompt":null}', '{"img_id":12}'],
        [json.dumps({"img_id": 11, "duration": 5, "prompt": "x" * 2049}), '{"img_id":12}'],
    ],
)
def test_invalid_multi_transition_stops_before_network(invoke, frames):
    """错误帧数组在认证请求之前拒绝，不创建任何任务。"""
    args = ["--json", "video", "multi-transition"]
    for frame in frames:
        args += ["--frame", frame]
    result, requests = invoke(args)
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--source-video-id", "21", "--video-media-id", "22"],
        ["--source-video-id", "21", "--sound-effect-content", "x" * 2049],
        ["--source-video-id", "21", "--webhook-id", "https://example.com"],
    ],
)
def test_invalid_sound_effect_stops_before_network(invoke, extra):
    """来源冲突和非法内容不进入音效生成请求。"""
    result, requests = invoke(["--json", "video", "sound-effect", *extra])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("command", ["ecommerce-native", "ecommerce-template"])
def test_ecommerce_named_product_reference(invoke, monkeypatch, region, command):
    args = [
        "--json",
        "agent",
        command,
        "--image-ref",
        '{"img_id":11,"ref_name":"product"}',
        "--prompt",
        "show product",
        "--duration",
        "15",
        "--language-code",
        "en-US",
    ]
    if command == "ecommerce-template":
        args += ["--video-style", "personal_review"]
    result, requests = invoke(args, region=region)
    assert result.exit_code == 0, result.output
    assert json.loads(requests[0].content)["img_references"] == [
        {"img_id": 11, "ref_name": "product"}
    ]


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--img-id", "12", "--image-ref", '{"img_id":11}'],
        ["--image-ref", '{"img_id":11,"type":"subject"}'],
    ],
)
def test_ecommerce_invalid_reference_combinations(invoke, extra):
    result, requests = invoke(
        [
            "--json",
            "agent",
            "ecommerce-native",
            "--prompt",
            "show",
            "--duration",
            "15",
            "--language-code",
            "en-US",
            *extra,
        ]
    )
    assert result.exit_code == 2
    assert not requests


CASES = [
    (
        [
            "video",
            "f2v",
            "--first-frame-img",
            "11",
            "--last-frame-img",
            "12",
            "--prompt",
            "transition",
        ],
        "video/transition/generate",
        {
            "first_frame_img": 11,
            "last_frame_img": 12,
            "prompt": "transition",
            "model": "v6",
            "duration": 5,
            "quality": "720p",
        },
    ),
    (
        ["video", "fusion", "--img-id", "11", "--img-id", "12", "--prompt", "together"],
        "video/fusion/generate",
        {
            "image_references": [{"img_id": 11}, {"img_id": 12}],
            "prompt": "together",
            "model": "v6",
            "quality": "720p",
            "aspect_ratio": "16:9",
        },
    ),
    (
        [
            "video",
            "fusion",
            "--reference-mode",
            "omni",
            "--video-ref",
            '{"video_media_id":13}',
            "--prompt",
            "motion",
        ],
        "video/fusion/generate",
        {
            "video_references": [{"video_media_id": 13}],
            "reference_mode": "omni",
            "prompt": "motion",
            "model": "v6",
            "quality": "720p",
            "aspect_ratio": "16:9",
        },
    ),
    (
        ["video", "extend", "--source-video-id", "21", "--prompt", "continue"],
        "video/extend/generate",
        {
            "source_video_id": 21,
            "prompt": "continue",
            "model": "v6",
            "duration": 5,
            "quality": "720p",
        },
    ),
    (
        ["video", "expand", "--video-media-id", "22", "--aspect-ratio", "9:16"],
        "video/expand/generate",
        {"video_media_id": 22, "aspect_ratio": "9:16", "quality": "720p"},
    ),
    (
        ["video", "upscale", "--source-video-id", "21", "--seed", "0"],
        "video/upscale/generate",
        {"source_video_id": 21, "seed": 0},
    ),
    (
        ["video", "restyle", "--source-video-id", "21", "--restyle-id", "31"],
        "video/restyle/generate",
        {"source_video_id": 21, "restyle_id": 31},
    ),
    (
        ["video", "restyle", "--video-media-id", "22", "--restyle-prompt", "watercolor"],
        "video/restyle/generate",
        {"video_media_id": 22, "restyle_prompt": "watercolor"},
    ),
    (
        ["video", "lipsync", "--source-video-id", "21", "--audio-media-id", "41"],
        "video/lip_sync/generate",
        {"source_video_id": 21, "audio_media_id": 41},
    ),
    (
        [
            "video",
            "lipsync",
            "--video-media-id",
            "22",
            "--tts-speaker-id",
            "Auto",
            "--tts-content",
            "你好",
        ],
        "video/lip_sync/generate",
        {"video_media_id": 22, "lip_sync_tts_speaker_id": "Auto", "lip_sync_tts_content": "你好"},
    ),
    (
        ["video", "avatar", "--img-id", "11", "--audio-media-id", "41"],
        "video/avatar/generate",
        {"img_id": 11, "audio_media_id": 41, "quality": "720p"},
    ),
    (
        [
            "video",
            "mimic",
            "--img-id",
            "11",
            "--source-video-id",
            "21",
            "--post-reference",
            "image",
        ],
        "video/mimic/generate",
        {"img_id": 11, "source_video_id": 21, "quality": "720p", "post_reference": "image"},
    ),
    (
        [
            "video",
            "swap",
            "--video-media-id",
            "22",
            "--keyframe-id",
            "0",
            "--mask-id",
            "0",
            "--img-id",
            "11",
        ],
        "video/swap/generate",
        {"video_media_id": 22, "keyframe_id": 0, "mask_id": "0", "img_id": 11, "quality": "540p"},
    ),
    (
        ["video", "modify", "--video-media-id", "22", "--prompt", "edit"],
        "video/modify/generate",
        {"video_media_id": 22, "prompt": "edit", "quality": "540p"},
    ),
    (
        [
            "agent",
            "ecommerce-native",
            "--img-id",
            "11",
            "--prompt",
            "sell",
            "--duration",
            "15",
            "--language-code",
            "zh-CN",
            "--no-lip-sync",
            "--no-bgm",
            "--no-caption",
        ],
        "video/agent/generate",
        {
            "agent_id": 414562414124107,
            "img_references": [{"img_id": 11}],
            "prompt": "sell",
            "duration": 15,
            "language_code": "zh-CN",
            "quality": "720p",
            "aspect_ratio": "9:16",
            "lip_sync_switch": False,
            "bgm_switch": False,
            "caption_switch": False,
        },
    ),
    (
        [
            "agent",
            "ecommerce-template",
            "--img-id",
            "11",
            "--prompt",
            "sell",
            "--duration",
            "30",
            "--language-code",
            "en-US",
            "--video-style",
            "personal_review",
            "--avatar",
            "auto",
        ],
        "video/agent/generate",
        {
            "agent_id": 414562414124108,
            "img_references": [{"img_id": 11}],
            "prompt": "sell",
            "duration": 30,
            "language_code": "en-US",
            "quality": "720p",
            "aspect_ratio": "9:16",
            "video_style": "personal_review",
            "avatar": "Auto",
        },
    ),
    (
        [
            "agent",
            "mv",
            "--audio-media-id",
            "41",
            "--mv-style",
            "Gothic Halloween",
            "--preserve-outfit",
            "--no-lip-sync",
            "--no-caption",
            "--seed",
            "0",
        ],
        "video/music_mv_agent/generate",
        {
            "mv_agent_type": "vibe_mv_v3_custom",
            "audio_media_id": 41,
            "mv_style": "Gothic Halloween",
            "quality": "720p",
            "aspect_ratio": "16:9",
            "preserve_outfit": True,
            "lip_sync_switch": False,
            "caption_switch": False,
            "seed": 0,
        },
    ),
]


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("args,path,payload", CASES, ids=[str(i) for i in range(len(CASES))])
def test_generation_contract(region, args, path, payload, invoke, monkeypatch):
    result, requests = invoke(["--json", *args], region=region)
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == PRODUCTION_URLS[region] + "/openapi/v2/" + path
    assert requests[0].headers["API-KEY"] == "synthetic-test-key"
    assert json.loads(requests[0].content) == payload
    output = json.loads(result.stdout)
    assert output["submission"] == "accepted"
    assert output["region"] == region


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize(
    "args,method,path",
    [
        (
            ["video", "mask", "--video-media-id", "22", "--keyframe-id", "1"],
            "POST",
            "/video/mask/selection",
        ),
        (["voice", "list"], "GET", "/video/tts_speaker?page_num=1&page_size=20&speaker_type=all"),
        (["video", "restyle-list"], "GET", "/video/restyle/list?page_num=1&page_size=50"),
    ],
)
def test_support_routes(region, args, method, path, invoke, monkeypatch):
    result, requests = invoke(["--json", *args], {"ErrCode": 0, "Resp": {}}, region=region)
    assert result.exit_code == 0, result.output
    assert len(requests) == 1 and requests[0].method == method
    assert str(requests[0].url) == PRODUCTION_URLS[region] + "/openapi/v2" + path
    assert "submission" not in json.loads(result.stdout)


@pytest.mark.parametrize(
    "command,extra",
    [
        ("extend", ["--prompt", "continue"]),
        ("expand", ["--aspect-ratio", "1:1"]),
        ("upscale", []),
        ("restyle", ["--restyle-id", "31"]),
        ("lipsync", ["--audio-media-id", "41"]),
        ("mimic", ["--img-id", "11"]),
        ("mask", ["--keyframe-id", "0"]),
        ("swap", ["--keyframe-id", "0", "--mask-id", "0", "--img-id", "11"]),
        ("modify", ["--prompt", "edit"]),
    ],
)
@pytest.mark.parametrize("sources", [[], ["--source-video-id", "21", "--video-media-id", "22"]])
def test_video_source_exclusivity(command, extra, sources, invoke):
    result, requests = invoke(["--json", "video", command, *extra, *sources])
    assert result.exit_code == 2 and not requests
    assert json.loads(result.stderr)["error"]["type"] == "validation"


@pytest.mark.parametrize(
    "command,base",
    [
        ("lipsync", ["--source-video-id", "21"]),
        ("avatar", ["--img-id", "11"]),
    ],
)
@pytest.mark.parametrize(
    "audio",
    [
        [],
        ["--tts-speaker-id", "Auto"],
        ["--tts-content", "hello"],
        ["--audio-media-id", "41", "--tts-speaker-id", "Auto", "--tts-content", "hello"],
    ],
)
def test_voice_exclusivity(command, base, audio, invoke):
    result, requests = invoke(["--json", "video", command, *base, *audio])
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize(
    "args",
    [
        ["video", "fusion", "--prompt", "x"],
        ["video", "fusion", "--prompt", "x", "--image-ref", '{"img_id":"11"}'],
        ["video", "fusion", "--prompt", "x", "--image-ref", '{"img_id":true}'],
        ["video", "fusion", "--prompt", "x", "--image-ref", '{"img_id":11,"account_id":12}'],
        ["video", "fusion", "--prompt", "x", "--image-ref", "[]"],
        [
            "video",
            "fusion",
            "--prompt",
            "x",
            "--video-ref",
            '{"source_video_id":21,"video_media_id":22}',
        ],
        ["video", "restyle", "--source-video-id", "21"],
        [
            "video",
            "restyle",
            "--source-video-id",
            "21",
            "--restyle-id",
            "31",
            "--restyle-prompt",
            "style",
        ],
        ["video", "modify", "--source-video-id", "21", "--prompt", "x", "--mask-id", "0"],
        [
            "video",
            "modify",
            "--source-video-id",
            "21",
            "--prompt",
            "x",
            "--mask-id",
            "0",
            "--keyframe-id",
            "1",
            "--mask-url",
            "https://example.com/mask.png",
        ],
        ["video", "upscale", "--source-video-id", "21", "--webhook-id", "url"],
        ["agent", "mv", "--audio-media-id", "41", "--mv-style", "Custom"],
        [
            "agent",
            "mv",
            "--audio-media-id",
            "41",
            "--mv-style",
            "Cinematic",
            "--style-img-id",
            "11",
        ],
    ],
)
def test_invalid_combinations_never_reach_api(args, invoke):
    result, requests = invoke(["--json", *args])
    assert result.exit_code == 2 and not requests, result.output


def test_modify_preserves_selection_order_and_keyframe_zero(invoke):
    result, requests = invoke(
        [
            "video",
            "modify",
            "--source-video-id",
            "21",
            "--prompt",
            "edit",
            "--img-id",
            "12",
            "--img-id",
            "11",
            "--mask-id",
            "0",
            "--mask-id",
            "1",
            "--keyframe-id",
            "0",
        ]
    )
    assert result.exit_code == 0
    payload = json.loads(requests[0].content)
    assert payload["mask_ids"] == ["0", "1"] and payload["img_ids"] == [12, 11]
    assert payload["keyframe_id"] == 0


def test_mv_custom_two_references_and_no_implicit_verification(invoke, tmp_path):
    lyrics = tmp_path / "lyrics.json"
    lyrics.write_text(json.dumps({"words": [{"start": 0, "end": 0.5, "word": "Hello"}]}))
    result, requests = invoke(
        [
            "agent",
            "mv",
            "--audio-media-id",
            "41",
            "--img-id",
            "11",
            "--style-img-id",
            "12",
            "--mv-style",
            "Custom",
            "--lyric-timestamp-file",
            str(lyrics),
            "--lyric-text",
            "timestamp takes priority",
            "--preserve-outfit",
            "--lip-sync",
        ]
    )
    assert result.exit_code == 0, result.output
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["image_references"] == [{"img_id": 11}]
    assert payload["style_img_references"] == [{"img_id": 12}]
    assert payload["lyric_timestamp"]["words"][0]["word"] == "Hello"
    assert payload["mv_agent_type"] == "vibe_mv_v3_custom" and payload["preserve_outfit"] is True


@pytest.mark.parametrize(
    "words",
    [
        [],
        [{"start": -1, "end": 1, "word": "a"}],
        [{"start": True, "end": 1, "word": "a"}],
        [{"start": 0, "end": float("nan"), "word": "a"}],
    ],
)
def test_bad_lyric_timestamps_fail_locally(words, invoke, tmp_path):
    path = tmp_path / "lyrics.json"
    path.write_text(json.dumps({"words": words}))
    result, requests = invoke(
        ["--json", "agent", "mv", "--audio-media-id", "41", "--lyric-timestamp-file", str(path)]
    )
    assert result.exit_code == 2 and not requests


@pytest.mark.parametrize(
    "status,normalized,exit_code",
    [
        ("running", "generating", 0),
        ("pending", "generating", 0),
        ("succeeded", "completed", 0),
        ("failed", "failed", 1),
        ("cancelled", "failed", 1),
        ("new-future-state", "unknown", 0),
    ],
)
def test_workflow_status_and_final_output(status, normalized, exit_code, invoke):
    result, _ = invoke(
        ["--json", "video", "get", "--id", "123"],
        {
            "ErrCode": 0,
            "Resp": {
                "video_id": 123,
                "status": status,
                "output": {"video": "https://example.com/final.mp4"},
            },
        },
    )
    assert result.exit_code == exit_code, result.output
    data = json.loads(result.stdout)
    assert data["task_status"] == normalized
    assert data["output_url"] == (
        "https://example.com/final.mp4" if status == "succeeded" else None
    )
    assert data["output_url_verified"] is False


def test_mask_to_swap_and_modify_workflow(invoke):
    mask, _ = invoke(
        ["--json", "video", "mask", "--video-media-id", "22", "--keyframe-id", "0"],
        {"ErrCode": 0, "Resp": {"keyframe_id": 0, "mask_info": [{"mask_id": "0"}]}},
    )
    info = json.loads(mask.stdout)["response"]["Resp"]
    for command, extra in [("swap", ["--img-id", "11"]), ("modify", ["--prompt", "replace"])]:
        result, requests = invoke(
            [
                "--json",
                "video",
                command,
                "--video-media-id",
                "22",
                "--keyframe-id",
                str(info["keyframe_id"]),
                "--mask-id",
                info["mask_info"][0]["mask_id"],
                *extra,
            ]
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(requests[0].content)
        assert payload["keyframe_id"] == 0 and payload["video_media_id"] == 22
        assert (payload["mask_id"] if command == "swap" else payload["mask_ids"][0]) == "0"


def test_mv_submits_without_separate_audio_verification(invoke):
    submitted, requests = invoke(["agent", "mv", "--audio-media-id", "41"])
    assert submitted.exit_code == 0 and len(requests) == 1
    assert json.loads(requests[0].content)["mv_agent_type"] == "vibe_mv_v3_custom"
