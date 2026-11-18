"""已安装命令的进程测试；不声称覆盖真实生产端到端。"""

import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from importlib.metadata import distribution, version
from importlib.resources import files
from pathlib import Path

import pytest


def _resolve_cli(name):
    path = shutil.which(name, path=os.path.dirname(sys.executable))
    if path:
        return [path]
    if os.environ.get("PIXVERSE_FORCE_INSTALLED") == "1":
        raise RuntimeError(f"{name} 未安装，请先 pip install -e '.[dev]'。")
    raise RuntimeError("进程测试要求安装 CLI。")


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["--version"],
        ["account", "balance", "--help"],
        ["account", "usage", "--help"],
        ["template", "list", "--help"],
        ["template", "generate", "--help"],
        ["template", "get", "--help"],
        ["image", "upload", "--help"],
        ["media", "upload", "--help"],
        ["video", "generate", "--help"],
        ["video", "from-image", "--help"],
        ["video", "get", "--help"],
        *[
            ["video", name, "--help"]
            for name in (
                "sound-effect",
                "multi-transition",
                "f2v",
                "fusion",
                "extend",
                "expand",
                "upscale",
                "restyle",
                "lipsync",
                "avatar",
                "mimic",
                "mask",
                "swap",
                "modify",
                "restyle-list",
            )
        ],
        ["voice", "list", "--help"],
        ["voice", "create", "--help"],
        ["voice", "delete", "--help"],
        ["agent", "ecommerce-native", "--help"],
        ["agent", "ecommerce-template", "--help"],
        ["agent", "mv", "--help"],
    ],
)
def test_installed_help_without_credentials(args):
    env = dict(os.environ)
    env.pop("PIXVERSE_OPENAPI_KEY", None)
    env.pop("PIXVERSE_REGION", None)
    result = subprocess.run(
        _resolve_cli("pixverse-api") + args, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout and not result.stderr


def test_missing_configuration_is_json():
    env = dict(os.environ)
    env.pop("PIXVERSE_OPENAPI_KEY", None)
    result = subprocess.run(
        _resolve_cli("pixverse-api") + ["--json", "account", "balance"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2 and not result.stdout
    assert "PIXVERSE_OPENAPI_KEY" in json.loads(result.stderr)["error"]["message"]


def test_installed_validation_redacts_openapi_key():
    key = "synthetic-validation-key"
    result = subprocess.run(
        [*_resolve_cli("pixverse-api"), "--json", "--region", key, "account", "balance"],
        env={**os.environ, "PIXVERSE_OPENAPI_KEY": key}, capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert key not in result.stdout + result.stderr
    assert "[REDACTED]" in json.loads(result.stderr)["error"]["message"]


@pytest.mark.parametrize(
    "args",
    [
        ["--json", "--env", "test", "account", "balance"],
        ["--json", "--base-url", "https://example.com", "account", "balance"],
        ["--json", "video", "get", "--id", "-1"],
        ["--json", "--timeout", "nan", "account", "balance"],
    ],
)
def test_invalid_options_fail_locally_as_json(args):
    result = subprocess.run(_resolve_cli("pixverse-api") + args, capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr)["error"]["type"] == "validation"


@pytest.mark.parametrize("args,field,allowed,state", [
    (["video", "avatar", "--img-id", "101", "--audio-media-id", "201", "--quality", "4k"],
     "quality", ["360p", "540p", "720p", "1080p"], "not_submitted"),
    (["voice", "list", "--type", "unknown"], "speaker_type", ["system", "custom", "all"],
     "not_applicable"),
])
def test_installed_enum_errors_describe_contract(args, field, allowed, state):
    result = subprocess.run(_resolve_cli("pixverse-api") + ["--json", *args],
                            capture_output=True, text=True)
    assert result.returncode == 2 and not result.stdout
    data = json.loads(result.stderr)
    assert data["stage"] == "validation" and data["submission_state"] == state
    assert data["error"]["fields"] == [field]
    assert data["error"]["code"] == "FIELD_ENUM"
    assert data["error"]["allowed_values"] == allowed


def test_installed_version_matches_distribution():
    """命令版本必须与安装包元数据一致，防止升级后仍显示旧版本。"""
    result = subprocess.run(
        _resolve_cli("pixverse-api") + ["--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert result.stdout.strip().endswith(version("pixverse-platform-cli"))


def test_distribution_registers_only_api_command():
    """B 端安装包不再注册与 C 端冲突的 pixverse 入口。"""
    entries = distribution("pixverse-platform-cli").entry_points
    scripts = {entry.name: entry.value for entry in entries if entry.group == "console_scripts"}
    assert scripts == {"pixverse-api": "cli.cli:main"}


def test_audio_verification_command_is_removed():
    result = subprocess.run(
        _resolve_cli("pixverse-api") + ["media", "verify-audio", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "No such command" in result.stderr


def test_installed_runtime_and_skill_match_current_source():
    """独立安装后的运行代码与Skill必须和交付源码一致，防止旧wheel回归。"""
    source = Path(__file__).resolve().parents[1] / "cli"
    package = files("cli")
    for path in [*source.glob("*.py"), source / "schemas.json", source / "skills" / "SKILL.md"]:
        relative = path.relative_to(source)
        assert (
            sha256(package.joinpath(*relative.parts).read_bytes()).digest()
            == sha256(path.read_bytes()).digest()
        ), str(relative)


def test_packaged_skill_available():
    assert (
        "pixverse-api" in files("cli").joinpath("skills/SKILL.md").read_text()
        and "--region" in files("cli").joinpath("skills/SKILL.md").read_text()
        and "PIXVERSE_REGION" not in files("cli").joinpath("skills/SKILL.md").read_text()
    )


@pytest.mark.parametrize("status,exit_code", [(1, 0), (5, 0), (7, 1), (8, 1)])
def test_installed_task_exit_code_with_simulated_http(status, exit_code):
    # 在子进程内注入 MockTransport，执行真实安装入口及 main 的退出码转换。
    bootstrap = """
import json, runpy, sys
import httpx
from cli import cli
response = json.loads(sys.argv[1])
real_client = cli.PlatformClient
def handler(request):
    assert request.url.host == 'app-api.pixverseai.cn'
    assert request.url.path == '/openapi/v2/video/result/123'
    return httpx.Response(200, json=response)
cli.PlatformClient = lambda config, **kw: real_client(
    config, transport=httpx.MockTransport(handler), **kw)
sys.argv = sys.argv[2:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    response = {"ErrCode": 0, "Resp": {"status": status}}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            bootstrap,
            json.dumps(response),
            *_resolve_cli("pixverse-api"),
            "--region",
            "cn",
            "--json",
            "video",
            "get",
            "--id",
            "123",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == exit_code, result.stderr
    assert json.loads(result.stdout)["response"]["Resp"]["status"] == status
    assert not result.stderr


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize(
    "args,path,field,value",
    [
        (
            ["video", "sound-effect", "--video-media-id", "22", "--no-original-sound"],
            "/video/sound_effect/generate",
            "original_sound_switch",
            False,
        ),
        (
            [
                "video",
                "multi-transition",
                "--frame",
                '{"img_id":11,"duration":5}',
                "--frame",
                '{"img_id":12}',
            ],
            "/video/multi_transition/generate",
            "multi_transition",
            [{"img_id": 11, "duration": 5}, {"img_id": 12}],
        ),
        (
            [
                "video",
                "f2v",
                "--prompt",
                "transition",
                "--first-frame-img",
                "11",
                "--last-frame-img",
                "12",
            ],
            "/video/transition/generate",
            "first_frame_img",
            11,
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
            "/video/swap/generate",
            "mask_id",
            "0",
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
            ],
            "/video/agent/generate",
            "agent_id",
            414562414124107,
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
                "15",
                "--language-code",
                "en-US",
                "--video-style",
                "polished_commercials",
            ],
            "/video/agent/generate",
            "agent_id",
            414562414124108,
        ),
        (
            ["agent", "mv", "--audio-media-id", "41", "--preserve-outfit"],
            "/video/music_mv_agent/generate",
            "mv_agent_type",
            "vibe_mv_v3_custom",
        ),
    ],
)
def test_installed_generation_contract(region, args, path, field, value):
    bootstrap = """
import json, runpy, sys
import httpx
from cli import cli
spec = json.loads(sys.argv[1])
real = cli.PlatformClient
def handler(request):
    assert request.url.host == spec['host']
    assert request.url.path == '/openapi/v2' + spec['path']
    assert request.method == 'POST'
    body = json.loads(request.content)
    assert body[spec['field']] == spec['value']
    return httpx.Response(200, json={'ErrCode': 0, 'Resp': {'video_id': 123}})
cli.PlatformClient = lambda config, **kw: real(config, transport=httpx.MockTransport(handler), **kw)
sys.argv = sys.argv[2:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    spec = {
        "host": "app-api.pixverseai.cn" if region == "cn" else "app-api.pixverse.ai",
        "path": path,
        "field": field,
        "value": value,
    }
    env = {**os.environ, "PIXVERSE_OPENAPI_KEY": "synthetic-test-key"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            bootstrap,
            json.dumps(spec),
            *_resolve_cli("pixverse-api"),
            "--region",
            region,
            "--json",
            *args,
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["submission"] == "accepted"


@pytest.mark.parametrize("region", ["cn", "global"])
@pytest.mark.parametrize("case", ["usage", "list", "standard", "workflow", "get", "failed"])
def test_installed_billing_and_templates(region, case):
    """安装入口按完整HTTP序列发现模板、提交或查询，不访问生产网络。"""
    prefix = "/openapi/v2"
    item = {"template_id": 11, "type": 1, "template_mode": "standard", "effect_type": "1"}
    get_meta = {
        "method": "GET",
        "path": prefix + "/video/effects/templates/list",
        "resp": {"effect_items": [item]},
    }
    if case == "usage":
        args = ["account", "usage", "--cursor", "opaque+/=="]
        steps = [
            {
                "method": "POST",
                "path": prefix + "/account/billing/usage-detail",
                "body": {"cursor": "opaque+/=="},
                "resp": {"items": [], "has_more": False, "next_cursor": ""},
            }
        ]
    elif case == "list":
        args, steps = ["template", "list"], [get_meta]
    elif case == "standard":
        args = [
            "template",
            "generate",
            "--id",
            "11",
            "--img-id",
            "21",
            "--model",
            "v5.6",
            "--duration",
            "5",
            "--quality",
            "720p",
        ]
        steps = [
            get_meta,
            {
                "method": "POST",
                "path": prefix + "/video/img/generate",
                "body": {
                    "template_id": 11,
                    "img_id": 21,
                    "model": "v5.6",
                    "duration": 5,
                    "quality": "720p",
                },
                "resp": {"video_id": 123},
            },
        ]
    elif case == "workflow":
        item.update(template_mode="workflow", outputs=[{"content_type": "video"}], input_limit=[])
        args = ["template", "generate", "--id", "11"]
        steps = [
            get_meta,
            {
                "method": "POST",
                "path": prefix + "/template/generate",
                "body": {"template_id": 11, "inputs": []},
                "resp": {"task_id": 456, "status": 5},
            },
        ]
    else:
        args = ["template", "get", "--id", "456"]
        steps = [
            {
                "method": "GET",
                "path": prefix + "/template/result/456",
                "resp": {"task_id": 456, "status": 7 if case == "failed" else 1, "contents": []},
            }
        ]
    bootstrap = """
import json, runpy, sys, httpx
from cli import cli
spec = json.loads(sys.argv[1])
real, calls = cli.PlatformClient, []
def handler(request):
    step = spec['steps'][len(calls)]
    calls.append(request)
    assert request.url.host == spec['host']
    assert request.method == step['method'] and request.url.path == step['path']
    assert request.headers['API-KEY'] == 'synthetic-test-key'
    if 'body' in step:
        assert json.loads(request.content) == step['body']
    if request.url.path.endswith('/templates/list'):
        assert request.url.params['type'] == '1'
    return httpx.Response(200, json={'ErrCode': 0, 'Resp': step['resp']})
cli.PlatformClient = lambda config, **kw: real(config, transport=httpx.MockTransport(handler), **kw)
sys.argv = sys.argv[2:]
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
finally:
    assert len(calls) == len(spec['steps'])
"""
    spec = {
        "host": "app-api.pixverseai.cn" if region == "cn" else "app-api.pixverse.ai",
        "steps": steps,
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            bootstrap,
            json.dumps(spec),
            *_resolve_cli("pixverse-api"),
            "--region",
            region,
            "--json",
            *args,
        ],
        env={**os.environ, "PIXVERSE_OPENAPI_KEY": "synthetic-test-key"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == (1 if case == "failed" else 0), result.stderr
    assert json.loads(result.stdout)["region"] == region
