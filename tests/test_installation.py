"""保护实际安装中出现的客户端混淆、目录覆盖和非标准打包回归。"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import install as installer
from scripts import install_skill


@pytest.mark.parametrize(
    ("client", "environment", "expected"),
    [
        ("workbuddy", {}, "/user/.codebuddy/skills"),
        (
            "workbuddy",
            {"CODEBUDDY_CONFIG_DIR": "/wb", "WORKBUDDY_CONFIG_DIR": "/models"},
            "/wb/skills",
        ),
        ("workbuddy", {"WORKBUDDY_CONFIG_DIR": "/models"}, "/user/.codebuddy/skills"),
        ("deepseek", {}, "/user/.dsh/skills"),
        ("deepseek", {"DSH_HOME": "/harness"}, "/harness/skills"),
        ("pi", {}, "/user/.pi/agent/skills"),
        ("pi", {"PI_CODING_AGENT_DIR": "/pi"}, "/pi/skills"),
        ("opencode", {}, "/user/.config/opencode/skills"),
        (
            "opencode",
            {"XDG_CONFIG_HOME": "/xdg", "OPENCODE_CONFIG": "/other/config.json"},
            "/xdg/opencode/skills",
        ),
    ],
)
def test_native_skill_root_respects_the_clients_override(client, environment, expected):
    assert install_skill.client_skills_dir(client, environment, Path("/user")) == Path(expected)


def test_running_parent_wins_over_four_installed_clients(monkeypatch):
    parents = {8: (7, None), 7: (6, "deepseek"), 6: (1, "pi")}
    monkeypatch.setattr(install_skill.os, "getppid", lambda: 8)
    monkeypatch.setattr(install_skill, "process_identity", lambda pid: parents[pid])
    environment = {
        name: "/configured"
        for name in ("DSH_HOME", "PI_CODING_AGENT_DIR", "OPENCODE_CONFIG", "CODEBUDDY_CONFIG_DIR")
    }
    assert install_skill.detect_client(environment) == ("deepseek", "parent_process")


def test_pi_process_title_is_recognized_when_the_executable_is_node(monkeypatch, tmp_path):
    process = tmp_path / "76"
    process.mkdir()
    (process / "stat").write_text("76 (pi) S 12 0 0")
    (process / "comm").write_text("pi\n")
    (process / "exe").symlink_to("/usr/local/bin/node")
    # 进程标题可替换原 argv；只凭名称即可识别，不要求读取后续参数。
    original_path = Path
    monkeypatch.setattr(
        install_skill, "Path", lambda value: tmp_path if value == "/proc" else original_path(value)
    )
    assert install_skill.process_identity(76) == (12, "pi")


def test_ambiguous_directory_markers_do_not_install_multiple_skills(monkeypatch):
    monkeypatch.setattr(install_skill.os, "getppid", lambda: 1)
    with pytest.raises(ValueError, match="无法唯一识别"):
        install_skill.detect_client({"DSH_HOME": "/dsh", "PI_CODING_AGENT_DIR": "/pi"})


def test_unavailable_process_lookup_allows_unambiguous_environment(monkeypatch):
    monkeypatch.setattr(install_skill.os, "getppid", lambda: 42)
    monkeypatch.setattr(
        install_skill,
        "process_identity",
        lambda pid: (_ for _ in ()).throw(PermissionError("process inspection is not available")),
    )
    assert install_skill.detect_client({"PI_CODING_AGENT_DIR": "/pi"}) == (
        "pi",
        "client_environment",
    )


@pytest.mark.parametrize(
    ("entrypoint", "client"),
    [
        ("/opt/workbuddy/dist/codebuddy-lite-wb.mjs", "workbuddy"),
        ("/usr/local/bin/dsh", "deepseek"),
        ("/opt/pkg/pi-coding-agent/dist/cli.js", "pi"),
        ("/opt/bin/opencode", "opencode"),
        ("/tmp/read-pixverse-pi-prompt.sh", None),
        ("/usr/bin/python3", None),
    ],
)
def test_identity_uses_entrypoints_not_prompt_fragments(entrypoint, client):
    assert install_skill.client_from_executable(entrypoint) == client


def test_explicit_client_and_custom_path_do_not_require_process_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(install_skill, "detect_client", lambda: pytest.fail("unexpected detection"))
    monkeypatch.setenv("CODEBUDDY_CONFIG_DIR", str(tmp_path / "wb"))
    assert install_skill.resolve_target("workbuddy")["skills_dir"] == str(tmp_path / "wb/skills")
    target = install_skill.resolve_target(skills_dir=tmp_path / "other")
    assert target["client"] == "custom"
    assert target["skills_dir"] == str(tmp_path / "other")


def test_complete_skill_install_and_backup_are_not_new_discovery_candidates(tmp_path):
    parent = tmp_path / "skills"
    result = install_skill.install(parent)
    destination = Path(result["skill_dir"])
    assert install_skill.REQUIRED <= install_skill.skill_files(destination).keys()
    assert install_skill.install(parent)["status"] == "unchanged"
    (destination / "SKILL.md").write_text("previous version")
    with pytest.raises(ValueError, match="已有不同版本"):
        install_skill.install(parent)
    updated = install_skill.install(parent, replace=True)
    backup = Path(updated["backup_dir"])
    assert not backup.is_relative_to(parent)
    assert (backup / "SKILL.md").read_text() == "previous version"
    assert install_skill.skill_files(destination) == install_skill.skill_files(install_skill.SOURCE)


def test_missing_reference_is_rejected_before_creating_destination(monkeypatch, tmp_path):
    source = tmp_path / "incomplete"
    source.mkdir()
    (source / "SKILL.md").write_text("incomplete")
    (source / "references").mkdir()
    for name in ("cli.md", "mcp.md", "showcase.md"):
        (source / "references" / name).write_text("Markdown reference without showcase data")
    monkeypatch.setattr(install_skill, "SOURCE", source)
    with pytest.raises(ValueError, match="源文件不完整"):
        install_skill.install(tmp_path / "target")
    assert not (tmp_path / "target").exists()


def test_cli_uses_original_source_and_isolated_build_metadata(monkeypatch, tmp_path):
    uv = tmp_path / "uv"
    binary = tmp_path / "bin/pixverse-api"
    binary.parent.mkdir()
    binary.touch()
    calls = []

    def execute(command, stage, timeout=240, *, report=None):
        calls.append(command)
        if command[1:] == ["tool", "dir", "--bin"]:
            return str(binary.parent)
        return "pixverse-api, version 0.8.0" if command[-1] == "--version" else ""

    monkeypatch.setattr(installer.shutil, "which", lambda name: str(uv if name == "uv" else binary))
    monkeypatch.setattr(installer, "checked_run", execute)
    result = installer.install_cli()
    assert calls[0] == [
        str(uv),
        "tool",
        "install",
        "--python",
        sys.executable,
        "--reinstall-package",
        "pixverse-platform-cli",
        str(installer.ROOT),
    ]
    assert [str(binary), "--help"] in calls
    assert result["help_verified"] and result["on_path"]


def test_uv_noncanonical_bin_path_does_not_trigger_a_false_path_warning(monkeypatch, tmp_path):
    binary = tmp_path / "bin/pixverse-api"
    binary.parent.mkdir()
    binary.touch()
    monkeypatch.setattr(
        installer.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else str(binary)
    )
    monkeypatch.setattr(
        installer,
        "checked_run",
        lambda command, *args, **kwargs: (
            str(tmp_path / "data/../bin") if command[1:] == ["tool", "dir", "--bin"] else "ok"
        ),
    )
    result = installer.install_cli()
    assert result["path"] == str(binary)
    assert result["on_path"]


def test_installation_failure_does_not_echo_private_package_index_settings(monkeypatch):
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, "private-index-value", "private-value"
        ),
    )
    with pytest.raises(ValueError) as error:
        installer.checked_run(["uv", "tool", "install"], "CLI 安装")
    assert "private" not in str(error.value)


def test_failed_cli_install_does_not_report_skill_success(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, "argv", ["install.py", "--skills-dir", str(tmp_path / "skills")])
    monkeypatch.setattr(installer.InstallTelemetry, "finish", lambda _report: None)
    monkeypatch.setattr(
        installer, "install_cli", lambda _report: (_ for _ in ()).throw(ValueError("CLI失败"))
    )
    assert installer.main() == 2
    payload = json.loads(capsys.readouterr().err)
    assert not payload["ok"] and payload["completed"] == {}
    assert not (tmp_path / "skills").exists()
