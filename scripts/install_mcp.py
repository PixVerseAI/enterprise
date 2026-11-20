"""Configure remote MCP and install the repository's complete shared skill."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__:
    from . import install_skill
    from .install_telemetry import InstallTelemetry
else:
    import install_skill
    from install_telemetry import InstallTelemetry

ENDPOINTS = {
    "global": "https://app-api.pixverse.ai/opanapi/mcp",
    "cn": "https://app-api.pixverseai.cn/opanapi/mcp",
}
ROOT = Path(__file__).resolve().parents[1]
AUTH = "Bearer ${PIXVERSE_OPENAPI_KEY}"


def read_json(path):
    if path.is_symlink():
        raise ValueError("MCP configuration must be a regular file, not a symlink.")
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise ValueError("Cannot parse the existing MCP JSON; it has not been changed.") from exc
    if not isinstance(value, dict):
        raise ValueError("MCP configuration must be a JSON object.")
    return value


def write_json(path, value):
    """Replace one configuration atomically without logging its existing contents."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".pixverse-mcp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configured_path(name, default):
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else default


def json_configuration(client, url, replace=False, *, report=None):
    home = Path.home()
    entry = {"type": "http", "url": url, "headers": {"Authorization": AUTH}}
    if client == "workbuddy":
        path = configured_path("CODEBUDDY_CONFIG_DIR", home / ".codebuddy") / ".mcp.json"
        keys = ("mcpServers",)
    elif client == "pi":
        path = configured_path("PI_CODING_AGENT_DIR", home / ".pi" / "agent") / "mcp.json"
        keys = ("mcpServers",)
    elif client == "opencode":
        result = subprocess.run(
            ["opencode", "--version"], capture_output=True, text=True, timeout=15, check=False
        )
        version = re.search(r"(?:^|\s)v?([12])\.\d+\.\d+", result.stdout)
        if result.returncode or not version:
            raise ValueError("Cannot identify the installed OpenCode configuration version.")
        directory = configured_path("XDG_CONFIG_HOME", home / ".config") / "opencode"
        path = configured_path("OPENCODE_CONFIG", directory / "opencode.json")
        if (not os.environ.get("OPENCODE_CONFIG") and not path.exists()
                and (directory / "opencode.jsonc").exists()):
            raise ValueError("Existing OpenCode JSONC needs a manual merge; nothing was changed.")
        keys = ("mcp", "servers") if version.group(1) == "2" else ("mcp",)
        entry = {
            "type": "remote", "url": url, "oauth": False,
            "headers": {"Authorization": "Bearer {env:PIXVERSE_OPENAPI_KEY}"},
        }
    else:
        raise ValueError("Unsupported JSON MCP client.")
    value = read_json(path)
    servers = value
    for key in keys:
        servers = servers.setdefault(key, {})
        if not isinstance(servers, dict):
            raise ValueError("Existing MCP server settings are not an object; no file was changed.")
    for alias, server in servers.items():
        if alias == "pixverse" or not isinstance(server, dict):
            continue
        if (server.get("url") in ENDPOINTS.values()
                and not server.get("disabled", False) and server.get("enabled", True)):
            raise ValueError("Another PixVerse connection is enabled; disable it first.")
    old = servers.get("pixverse")
    managed = isinstance(old, dict) and old.get("url") in ENDPOINTS.values() and old.get(
        "headers", {}
    ) == entry["headers"] and set(old) <= set(entry) | {"disabled", "enabled"}
    if old is not None and old != entry and not managed and not replace:
        raise ValueError("Existing pixverse settings differ; review them before using --replace.")
    if report:
        report.action = "install" if old is None else ("noop" if old == entry else "reconfigure")
    servers["pixverse"] = entry
    return path, value


def deepseek_configuration(profile, url, replace=False, check=False):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", profile):
        raise ValueError("Invalid DeepSeek profile name.")
    binary = shutil.which("dsh")
    node = shutil.which("node")
    if not binary or not node:
        raise ValueError("DeepSeek Harness and Node.js must be installed first.")
    directory = configured_path("DSH_HOME", Path.home() / ".dsh") / "profiles" / profile
    if not directory.is_dir():
        raise ValueError("DeepSeek profile does not exist; initialize that profile first.")
    command = [node, str(ROOT / "scripts" / "configure_dsh_mcp.mjs"),
               str(Path(binary).resolve()), str(directory / "cordis.patch.yml"), url]
    if replace:
        command.append("--replace")
    if check:
        command.append("--check")
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode:
        # Never relay a parser error containing an existing credential or configuration line.
        raise ValueError(
            "Cannot update DeepSeek; check profile YAML and existing PixVerse entries."
        )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=install_skill.CLIENTS, default="auto")
    parser.add_argument("--region", choices=ENDPOINTS, default="global",
                        help="Default: global regardless of language; use cn explicitly.")
    parser.add_argument("--profile", default="tui", help="DeepSeek profile in use (default: tui).")
    parser.add_argument("--replace", action="store_true",
                        help="Replace reviewed conflicting settings or skill.")
    options = parser.parse_args()
    report = InstallTelemetry("mcp", options.client, options.region)
    try:
        return install(options, report)
    finally:
        report.finish()


def install(options, report):
    completed = report.completed
    try:
        target = install_skill.resolve_target(options.client)
        client = target["client"]
        report.client = client
        url = ENDPOINTS[options.region]
        report.step("skill_preflight", "skill_source_invalid")
        # Preflight the full original skill before modifying client settings.
        expected = install_skill.skill_files(install_skill.SOURCE)
        if not install_skill.REQUIRED <= expected.keys():
            raise ValueError("Repository skill is incomplete; use a complete clone.")
        destination = Path(target["skills_dir"]) / install_skill.NAME
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            raise ValueError("Skill target must be a regular directory.")
        if destination.exists() and not options.replace:
            if install_skill.skill_files(destination) != expected:
                report.step("skill_preflight", "skill_conflict")
                raise ValueError("Installed skill differs; review it before using --replace.")
        report.step("mcp_config_preflight", "mcp_config_invalid")
        if client == "deepseek":
            deepseek_configuration(options.profile, url, options.replace, check=True)
        else:
            path, value = json_configuration(client, url, options.replace, report=report)
        report.step("skill_install", "skill_install_failed")
        completed["skill"] = install_skill.install(Path(target["skills_dir"]), options.replace)
        report.step("mcp_config_write", "mcp_config_write_failed")
        if client == "deepseek":
            config = deepseek_configuration(options.profile, url, options.replace)
            config_path = config["path"]
            report.action = config.get("action", "unknown")
        else:
            write_json(path, value)
            config_path = str(path)
        completed["mcp"] = {"path": config_path, "alias": "pixverse", "url": url}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        if isinstance(exc, subprocess.TimeoutExpired):
            report.error_code = "step_timeout"
        error = (str(exc) if isinstance(exc, ValueError)
                 else "Installation failed; check client permissions and runtime.")
        print(json.dumps({"ok": False, "error": error, "completed": completed}), file=sys.stderr)
        return 2
    print(json.dumps({
        "ok": True, **target, **completed, "region": options.region,
        "cli_installed": False, "key_source": "PIXVERSE_OPENAPI_KEY in the client process",
        "discovery": "requires_new_session_verification",
    }))
    report.success = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
