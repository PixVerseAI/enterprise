"""Protect native config roots, original skill installation, and explicit service selection."""

import json
import subprocess
import sys

import pytest

from scripts import install_mcp, install_skill


@pytest.fixture(autouse=True)
def isolate_installation_from_telemetry(monkeypatch):
    monkeypatch.setattr(install_mcp.InstallTelemetry, "finish", lambda _report: None)


@pytest.mark.parametrize("client", ["workbuddy", "pi", "opencode"])
def test_native_config_preserves_other_servers_and_switches_one_alias(
    client, monkeypatch, tmp_path
):
    for name in ("CODEBUDDY_CONFIG_DIR", "PI_CODING_AGENT_DIR", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(tmp_path / name))
    monkeypatch.delenv("OPENCODE_CONFIG", raising=False)
    monkeypatch.setattr(install_mcp.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a, 0, "opencode v2.2.7", ""))
    path, value = install_mcp.json_configuration(client, install_mcp.ENDPOINTS["global"])
    if client == "workbuddy":
        assert path == tmp_path / "CODEBUDDY_CONFIG_DIR/.mcp.json"
    servers = value["mcp"]["servers"] if client == "opencode" else value["mcpServers"]
    servers["other"] = {"url": "https://example.com/mcp", "custom": {"keep": True}}
    value["unrelated"] = {"keep": True}
    install_mcp.write_json(path, value)
    _, switched = install_mcp.json_configuration(client, install_mcp.ENDPOINTS["cn"])
    updated = switched["mcp"]["servers"] if client == "opencode" else switched["mcpServers"]
    assert set(updated) == {"pixverse", "other"}
    assert updated["pixverse"]["url"] == install_mcp.ENDPOINTS["cn"]
    assert updated["other"] == servers["other"] and switched["unrelated"] == {"keep": True}
    assert "PIXVERSE_OPENAPI_KEY" in updated["pixverse"]["headers"]["Authorization"]


def test_opencode_selected_config_wins_but_skill_root_stays_native(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    selected = tmp_path / "selected/model-settings.json"
    monkeypatch.setenv("OPENCODE_CONFIG", str(selected))
    install_mcp.write_json(selected, {"model": "runtime/gpt-6-luna", "mcp": {"servers": {}}})
    monkeypatch.setattr(install_mcp.subprocess, "run", lambda *a, **k:
                        subprocess.CompletedProcess(a, 0, "opencode v2.2.7", ""))
    path, value = install_mcp.json_configuration("opencode", install_mcp.ENDPOINTS["cn"])
    assert path == selected and value["model"] == "runtime/gpt-6-luna"
    assert value["mcp"]["servers"]["pixverse"]["url"] == install_mcp.ENDPOINTS["cn"]
    assert install_skill.client_skills_dir("opencode") == tmp_path / "xdg/opencode/skills"


def test_default_ignores_locale_and_installs_original_skill(monkeypatch, tmp_path, capsys):
    root = tmp_path / "pi"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(root))
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    monkeypatch.setenv("PIXVERSE_OPENAPI_KEY", "synthetic-test-only-secret")
    monkeypatch.setattr(sys, "argv", ["install_mcp.py", "--client", "pi"])
    assert install_mcp.main() == 0
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["region"] == "global" and not result["cli_installed"]
    assert result["mcp"]["url"] == install_mcp.ENDPOINTS["global"]
    assert "synthetic-test-only-secret" not in output.out + output.err
    assert install_skill.skill_files(root / "skills/pixverse-api") == install_skill.skill_files(
        install_skill.SOURCE
    )
    assert install_mcp.main() == 0
    assert json.loads(capsys.readouterr().out)["skill"]["status"] == "unchanged"
    assert (root / "mcp.json").stat().st_mode & 0o777 == 0o600


def test_explicit_cn_and_incomplete_skill_preflight(monkeypatch, tmp_path, capsys):
    root = tmp_path / "pi"
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(root))
    monkeypatch.setattr(sys, "argv", ["install_mcp.py", "--client", "pi", "--region", "cn"])
    assert install_mcp.main() == 0
    assert json.loads(capsys.readouterr().out)["mcp"]["url"] == install_mcp.ENDPOINTS["cn"]
    before = (root / "mcp.json").read_bytes()
    monkeypatch.setattr(install_skill, "SOURCE", tmp_path / "missing-source")
    assert install_mcp.main() == 2
    assert (root / "mcp.json").read_bytes() == before


def test_second_enabled_pixverse_alias_is_not_added(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path))
    original = {"mcpServers": {"pixverse-5": {"url": install_mcp.ENDPOINTS["cn"]}}}
    install_mcp.write_json(tmp_path / "mcp.json", original)
    with pytest.raises(ValueError, match="Another PixVerse"):
        install_mcp.json_configuration("pi", install_mcp.ENDPOINTS["global"])
    assert install_mcp.read_json(tmp_path / "mcp.json") == original


def test_conflict_requires_review_and_keeps_unrelated_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path))
    original = {"mcpServers": {"pixverse": {"url": "https://example.com/mcp"}}, "keep": 42}
    install_mcp.write_json(tmp_path / "mcp.json", original)
    with pytest.raises(ValueError, match="review"):
        install_mcp.json_configuration("pi", install_mcp.ENDPOINTS["global"])
    _, value = install_mcp.json_configuration("pi", install_mcp.ENDPOINTS["cn"], replace=True)
    assert value["keep"] == 42
    assert install_mcp.read_json(tmp_path / "mcp.json") == original


def test_invalid_json_does_not_echo_its_contents(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PI_CODING_AGENT_DIR", str(tmp_path))
    (tmp_path / "mcp.json").write_text('{"private":"synthetic-secret",broken')
    monkeypatch.setattr(sys, "argv", ["install_mcp.py", "--client", "pi"])
    assert install_mcp.main() == 2
    output = capsys.readouterr()
    assert "synthetic-secret" not in output.out + output.err
    assert json.loads(output.err)["completed"] == {}
    assert not (tmp_path / "skills").exists()
