"""协议回归仅使用合成凭据和 MockTransport，不访问真实 Platform。"""

import json

import httpx
import pytest

from cli.protocol import SCHEMAS


def body(result):
    return json.loads(result.stdout if result.stdout else result.stderr)


def contract_constraints(schema):
    """仅忽略Schema自身的description，保留字段名、默认值和枚举字面量。"""
    if not isinstance(schema, dict):
        return schema
    mappings = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
    singles = {"items", "contains", "additionalProperties", "unevaluatedProperties",
               "unevaluatedItems", "propertyNames", "not", "if", "then", "else", "contentSchema"}
    sequences = {"allOf", "anyOf", "oneOf", "prefixItems"}
    result = {}
    for key, value in schema.items():
        if key == "description":
            continue
        if key in mappings:
            value = {name: contract_constraints(item) for name, item in value.items()}
        elif key in singles:
            value = contract_constraints(value)
        elif key in sequences:
            value = [contract_constraints(item) for item in value]
        result[key] = value
    return result


def test_contract_comparison_ignores_schema_descriptions():
    """CLI和MCP可独立维护说明，不因嵌套说明文字不同而判定协议漂移。"""
    left = {"description": "CLI", "properties": {"prompt": {
        "type": "string", "description": "CLI prompt",
    }}}
    right = {"description": "MCP", "properties": {"prompt": {
        "type": "string", "description": "MCP prompt",
    }}}
    assert contract_constraints(left) == contract_constraints(right)


@pytest.mark.parametrize("left,right", [
    ({"type": "string"}, {"type": "integer"}),
    ({"enum": ["720p"]}, {"enum": ["1080p"]}),
    ({"default": 20}, {"default": 50}),
    ({"required": ["img_id"]}, {"required": ["video_id"]}),
    ({"properties": {"description": {"type": "string"}}},
     {"properties": {"description": {"type": "integer"}}}),
    ({"enum": [{"description": "literal A"}]}, {"enum": [{"description": "literal B"}]}),
    ({"allOf": [{"properties": {"duration": {"maximum": 5}}}]},
     {"allOf": [{"properties": {"duration": {"maximum": 8}}}]}),
])
def test_contract_comparison_preserves_actual_constraints(left, right):
    """说明可不同，真实字段、枚举、默认值和组合约束变化仍必须报差异。"""
    assert contract_constraints(left) != contract_constraints(right)




def test_all_31_business_commands_have_contracts():
    from cli.cli import cli

    names = {f"{group.name}_{name.replace('-', '_')}"
             for group in cli.commands.values() for name in group.commands}
    assert names == set(SCHEMAS) and len(names) == 31


def test_cli_help_fields_enums_and_defaults_match_contract():
    from cli.cli import cli

    aliases = {"creation_type": "creation_types", "credits_status": "credits_statuses",
               "frame": "frames", "raw_inputs": "inputs", "image_ref": "image_references",
               "video_ref": "video_references", "lyric_timestamp_file": "lyric_timestamp"}
    array_images = {"video_fusion", "video_modify", "template_generate",
                    "agent_ecommerce_native", "agent_ecommerce_template"}
    for group in cli.commands.values():
        for name, command in group.commands.items():
            tool = f"{group.name}_{name.replace('-', '_')}"
            schema, covered = SCHEMAS[tool], set()
            for parameter in command.params:
                field = aliases.get(parameter.name, parameter.name)
                if field == "file":
                    continue
                if parameter.name == "img_id" and tool in array_images:
                    field = "img_ids"
                if tool == "video_modify" and parameter.name in ("mask_id", "mask_url"):
                    field = parameter.name + "s"
                if tool == "template_list" and parameter.name == "template_id":
                    field = "template_ids"
                covered.add(field)
                spec = schema["properties"][field]
                if tool not in ("image_upload", "media_upload"):
                    required = field in schema.get("required", [])
                    assert parameter.required == required, (tool, field)
                choices = getattr(parameter.type, "choices", None)
                enum = spec.get("enum") or next((s["enum"] for s in spec.get("anyOf", [])
                                                if "enum" in s), None)
                if choices is not None and enum is not None:
                    assert set(map(str, choices)) == set(map(str, enum)), (tool, field)
                if "default" in spec:
                    actual = parameter.default
                    if not isinstance(actual, (str, int, float, bool, type(None), tuple, list)):
                        actual = None
                    if parameter.multiple:
                        actual = list(actual or [])
                    if tool in ("template_list", "voice_list") and field == "page_size":
                        actual = int(actual)
                    assert actual == spec["default"], (tool, field)
            assert covered == set(schema["properties"]), tool


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("prompt", [None, "", " ", "x" * 5000])
def test_i2v_optional_prompt_preserves_intent(region, prompt, invoke, monkeypatch):
    args = ["--json", "video", "from-image", "--img-id", "101"]
    result, requests = invoke(
        args + ([] if prompt is None else ["--prompt", prompt]), region=region
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(requests[0].content)
    assert ("prompt" in payload) == (prompt is not None)
    if prompt is not None:
        assert payload["prompt"] == prompt
    assert "aspect_ratio" not in payload


@pytest.mark.parametrize("references", [
    ["--img-id", "101"],
    ["--video-ref", '{"video_media_id":201}', "--reference-mode", "omni"],
])
@pytest.mark.parametrize("duration", [None, 0, 5])
def test_fusion_duration_not_rewritten(references, duration, invoke):
    args = ["--json", "video", "fusion", "--prompt", "x", "--aspect-ratio", "auto",
            "--no-audio", "--seed", "0", *references]
    result, requests = invoke(args + ([] if duration is None else ["--duration", str(duration)]))
    assert result.exit_code == 0, result.output
    payload = json.loads(requests[0].content)
    assert ("duration" in payload) == (duration is not None)
    if duration is not None:
        assert payload["duration"] == duration
    assert payload["aspect_ratio"] == "auto"
    assert payload["seed"] == 0 and payload["generate_audio_switch"] is False


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("quality", ["360p", "540p", "720p", "1080p"])
def test_avatar_quality_contract(region, quality, invoke, monkeypatch):
    result, requests = invoke(["--json", "video", "avatar", "--img-id", "101",
                               "--audio-media-id", "201", "--quality", quality,
                               "--prompt", "x" * 2048], region=region)
    assert result.exit_code == 0, result.output
    assert json.loads(requests[0].content)["quality"] == quality


def test_avatar_prompt_limit_is_formal_validation(invoke):
    result, requests = invoke(["--json", "video", "avatar", "--img-id", "101",
                               "--audio-media-id", "201", "--prompt", "x" * 2049])
    error = body(result)
    assert result.exit_code == 2 and not requests
    assert error["submission_state"] == "not_submitted"
    assert error["error"]["fields"] == ["prompt"]
    assert error["error"]["code"] == "FIELD_RANGE"


@pytest.mark.parametrize("keyframe", [None, 0, 27])
def test_mask_keyframe_optional_and_preserved(keyframe, invoke):
    args = ["--json", "video", "mask", "--video-media-id", "201"]
    result, requests = invoke(args + ([] if keyframe is None else ["--keyframe-id", str(keyframe)]))
    assert result.exit_code == 0, result.output
    payload = json.loads(requests[0].content)
    assert ("keyframe_id" in payload) == (keyframe is not None)
    if keyframe is not None:
        assert payload["keyframe_id"] == keyframe


def test_voice_list_defaults_to_combined_endpoint(invoke):
    result, requests = invoke(["--json", "voice", "list"])
    assert result.exit_code == 0
    assert requests[0].url.path == "/openapi/v2/video/tts_speaker"
    assert dict(requests[0].url.params) == {
        "page_num": "1", "page_size": "20", "speaker_type": "all",
    }
    assert body(result)["submission_state"] == "not_applicable"


DEFERRED = [
    ["video", "fusion", "--prompt", "x", "--video-ref", '{"video_media_id":201}'],
    ["video", "fusion", "--prompt", "x", "--reference-mode", "omni", "--model", "c1",
     "--img-id", "101"],
    ["video", "fusion", "--prompt", "x", "--reference-mode", "omni", "--duration", "5",
     "--video-ref", '{"video_media_id":201}'],
    ["video", "fusion", "--prompt", "x", *[part for i in range(11)
                                            for part in ("--img-id", str(i + 101))]],
    ["video", "fusion", "--prompt", "x", "--reference-mode", "omni",
     *[part for i in range(3)
       for part in ("--video-ref", json.dumps({"video_media_id": i + 201}))]],
    ["video", "fusion", "--prompt", "x", "--image-ref", '{"img_id":101,"ref_name":"same"}',
     "--image-ref", '{"img_id":102,"ref_name":"same"}'],
    ["video", "generate", "--prompt", "x", "--negative-prompt", "x" * 2049],
    ["video", "from-image", "--img-id", "101", "--negative-prompt", "x" * 2049],
    ["video", "f2v", "--first-frame-img", "101", "--last-frame-img", "102", "--prompt", "x",
     "--negative-prompt", "x" * 2049],
    ["video", "restyle", "--video-media-id", "201", "--restyle-id", "10",
     "--negative-prompt", "x" * 2049],
    ["video", "avatar", "--img-id", "101", "--tts-speaker-id", "x" * 257,
     "--tts-content", "a valid synthetic sentence for a speaker sample"],
    ["video", "lipsync", "--video-media-id", "201", "--tts-speaker-id", "speaker",
     "--tts-content", "x" * 5001],
    ["agent", "ecommerce-native", "--prompt", "x", "--duration", "15", "--language-code", "en-US",
     "--avatar", "not-valid", *[p for i in range(6) for p in ("--img-id", str(101 + i))]],
]


@pytest.mark.parametrize("args", DEFERRED, ids=[f"deferred-{i}" for i in range(len(DEFERRED))])
def test_dynamic_business_validation_is_forwarded_once(args, invoke):
    result, requests = invoke(["--json", *args], response={
        "ErrCode": 4001, "ErrMsg": "Platform business rule",
        "Error": {"Message": "Platform decides this combination", "Field": "synthetic"},
    })
    data = body(result)
    assert result.exit_code == 1 and len(requests) == 1
    assert data["stage"] == "upstream" and data["submission_state"] == "rejected"
    assert data["error"]["message"] == "Platform decides this combination"
    assert data["error"]["response"]["Error"]["Field"] == "synthetic"


@pytest.mark.parametrize("frames", [
    [{"img_id": 101, "duration": 1}] * 7 + [{"img_id": 102}],
    [{"img_id": 101}, {"img_id": 102}],
    [{"img_id": 101, "duration": 0}, {"img_id": 102}],
    [{"img_id": 101, "duration": 9}, {"img_id": 102}],
    [{"img_id": 101, "duration": 6}, {"img_id": 102, "duration": 5}, {"img_id": 103}],
    [{"img_id": 101, "duration": 5}, {"img_id": 102, "duration": 1}],
])
def test_multitransition_dynamic_limits_not_local(frames, invoke):
    args = ["--json", "video", "multi-transition"]
    for frame in frames:
        args += ["--frame", json.dumps(frame)]
    result, requests = invoke(args, response={"ErrCode": 4001, "ErrMsg": "Platform frame limit"})
    assert result.exit_code == 1 and len(requests) == 1
    assert json.loads(requests[0].content)["multi_transition"] == frames
    assert body(result)["submission_state"] == "rejected"


@pytest.mark.parametrize("words", [
    [{"start": 1, "end": 0, "word": "a"}],
    [{"start": 0, "end": 2, "word": "a"}, {"start": 1, "end": 3, "word": "b"}],
    [{"start": 0, "end": 1, "word": " "}],
    [{"start": 0, "end": 1, "word": "a"}] * 5001,
])
def test_lyric_business_rules_go_to_platform(words, invoke, tmp_path):
    path = tmp_path / "lyrics.json"
    path.write_text(json.dumps({"words": words}))
    result, requests = invoke(["--json", "agent", "mv", "--audio-media-id", "201",
                               "--lyric-timestamp-file", str(path)],
                              response={"ErrCode": 4001, "ErrMsg": "Platform lyric rule"})
    assert result.exit_code == 1 and len(requests) == 1
    assert json.loads(requests[0].content)["lyric_timestamp"] == {"words": words}
    assert body(result)["submission_state"] == "rejected"


@pytest.mark.parametrize("filters", [
    ["--start-time", "2026-11-02 00:00:00", "--end-time", "2026-11-01 00:00:00"],
    ["--start-time", "2026-11-01 00:00:00", "--end-time", "2026-12-02 00:00:00"],
    ["--start-time", "2026-11-01 00:00:00", "--end-time", "2026-11-02 00:00:00",
     "--creation-type", " "],
    ["--cursor", " "],
])
def test_usage_business_rules_are_read_only_upstream(filters, invoke):
    result, requests = invoke(["--json", "account", "usage", *filters],
                              response={"ErrCode": 4001, "ErrMsg": "Platform time window"})
    assert result.exit_code == 1 and len(requests) == 1
    assert body(result)["submission_state"] == "not_applicable"


@pytest.mark.parametrize("kind,id_field", [("image", "img_id"), ("media", "media_id")])
@pytest.mark.parametrize("identifier", [None, True, "101", 0, -1, 2**64])
def test_upload_invalid_response_id_means_unknown(kind, id_field, identifier, invoke):
    result, requests = invoke(["--json", kind, "upload", "--url", "https://example.com/input"],
                              response={"ErrCode": 0, "Resp": {id_field: identifier}})
    data = body(result)
    assert result.exit_code == 1 and len(requests) == 1
    assert data["submission_state"] == "unknown" and data["error"]["trace_id"]


@pytest.mark.parametrize("identifier", [None, True, "101", 0, -1, 2**64])
def test_create_invalid_response_id_means_unknown(identifier, invoke):
    result, requests = invoke(["--json", "video", "generate", "--prompt", "x"],
                              response={"ErrCode": 0, "Resp": {"video_id": identifier}})
    assert result.exit_code == 1 and len(requests) == 1
    assert body(result)["submission_state"] == "unknown"


@pytest.mark.parametrize("url", ["http://example.com/x", "https://example.com/x#part",
                                 "https://example.com:8443/x", "https://user:pass@example.com/x",
                                 "https://example.com/a b"])
def test_url_contract_is_same_for_upload_and_mask(url, invoke):
    for args in (["image", "upload", "--url", url],
                 ["video", "modify", "--video-media-id", "201", "--prompt", "x",
                  "--mask-url", url]):
        result, requests = invoke(["--json", *args])
        assert result.exit_code == 2 and not requests
        assert body(result)["error"]["code"] == "FIELD_FORMAT"


def test_supplier_domain_has_no_local_allowlist(invoke):
    result, requests = invoke(["--json", "media", "upload", "--url",
                               "https://noah-ai-generate.s3.cn-south-1.qiniucs.com/music.wav"])
    assert result.exit_code == 0 and len(requests) == 1


@pytest.mark.parametrize("speaker_id", ["CUSTOM_abc", "custom_", "custom_../secret"])
def test_custom_voice_ids_are_preserved_and_path_encoded(speaker_id, invoke):
    result, requests = invoke(["--json", "voice", "delete", "--speaker-id", speaker_id],
                              response={"ErrCode": 0, "Resp": None})
    assert result.exit_code == 0 and len(requests) == 1
    assert requests[0].url.path.startswith("/openapi/v2/video/tts_speaker/custom_") or (
        requests[0].url.path.startswith("/openapi/v2/video/tts_speaker/CUSTOM_"))
    if "/" in speaker_id:
        assert b"%2F" in requests[0].url.raw_path and b"%2E" in requests[0].url.raw_path


@pytest.mark.parametrize("status", ["1", "new-state", 99])
def test_unknown_task_status_never_means_completed(status, invoke):
    result, _ = invoke(["--json", "video", "get", "--id", "101"],
                       response={"ErrCode": 0, "Resp": {"status": status, "url": "https://example.com/x"}})
    data = body(result)
    assert result.exit_code == 0 and data["task_status"] == "unknown"
    assert data["output_url"] is None and data["submission_state"] == "not_applicable"


@pytest.mark.parametrize("status", [7, 8, "failed"])
def test_failed_terminal_task_sets_ok_false(status, invoke):
    result, _ = invoke(["--json", "video", "get", "--id", "101"],
                       response={"ErrCode": 0, "Resp": {"status": status}})
    assert result.exit_code == 1 and body(result)["ok"] is False


@pytest.mark.parametrize("query", [False, True])
def test_write_timeout_and_read_query_timeout_are_distinct(query, monkeypatch):
    from click.testing import CliRunner

    from cli import cli as commands
    from cli.client import PlatformClient

    requests = []

    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout("synthetic timeout")

    monkeypatch.setattr(commands, "PlatformClient", lambda config, **kw: PlatformClient(
        config, transport=httpx.MockTransport(handler), **kw))
    args = (["account", "usage", "--start-time", "2026-11-01 00:00:00",
             "--end-time", "2026-11-02 00:00:00"] if query
            else ["video", "generate", "--prompt", "x"])
    result = CliRunner().invoke(commands.cli, ["--json", *args])
    assert result.exit_code == 1 and len(requests) == 1
    assert body(result)["submission_state"] == ("not_applicable" if query else "unknown")


def test_formal_extend_limit_is_retained(invoke):
    result, requests = invoke(["--json", "video", "extend", "--video-media-id", "201",
                               "--prompt", "x", "--negative-prompt", "x" * 2049])
    assert result.exit_code == 2 and not requests
    assert body(result)["error"]["code"] == "FIELD_RANGE"
