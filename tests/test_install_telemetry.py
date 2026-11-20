"""Exercise normal installer entry points against a local HTTP collector."""

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from scripts import install, install_telemetry

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import sys
from pathlib import Path
from scripts import install, install_mcp, install_skill, install_telemetry

integration, outcome, endpoint, destination, baseline = sys.argv[1:]
root = Path(destination)
install_telemetry.ENDPOINTS.update({"cn": endpoint, "global": endpoint})
if baseline == "baseline":
    install_telemetry.InstallTelemetry.finish = lambda _report: None

def fail(*args, **kwargs):
    raise OSError("synthetic failure")

if outcome == "failed":
    install_skill.resolve_target = fail

if integration == "cli":
    def fake_cli(*args):
        artifact = root / "pixverse-api"
        artifact.write_bytes(b"installed CLI")
        return {"path": str(artifact), "version": "pixverse-api, version 0.8.0",
                "on_path": False, "help_verified": True}
    install.install_cli = fake_cli
    if outcome == "partial":
        install_skill.install = fail
    sys.argv = ["install.py", "--client", "pi"]
    sys.exit(install.main())

if outcome == "partial":
    install_mcp.write_json = fail
sys.argv = ["install_mcp.py", "--client", "pi", "--region", "cn"]
sys.exit(install_mcp.main())
"""


@pytest.fixture
def collector():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            payload = self.rfile.read(int(self.headers["Content-Length"]))
            authenticated = "Authorization" in self.headers
            self.server.events.append((self.path, json.loads(payload), authenticated))
            self.server.received.set()
            if self.server.mode == "timeout":
                self.connection.settimeout(4)
                try:
                    assert self.connection.recv(1) == b""
                    self.server.disconnected.set()
                except TimeoutError:
                    pass
                return
            self.send_response({"success": 204, "failure": 503, "redirect": 307}[self.server.mode])
            if self.server.mode == "redirect":
                self.send_header("Location", "/unexpected")
            self.end_headers()

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        server.events = []
        server.received = threading.Event()
        server.disconnected = threading.Event()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()


@pytest.mark.parametrize("integration", ["cli", "mcp"])
@pytest.mark.parametrize("outcome", ["success", "partial", "failed"])
@pytest.mark.parametrize("mode", [
    "success", "failure", "timeout", "redirect", "connection_refused",
])
def test_reporting_does_not_change_install(tmp_path, collector, integration, outcome, mode):
    location = tmp_path / "installer"
    collector.mode = mode
    port = collector.server_port
    refused = socket.socket()
    refused.bind(("127.0.0.1", 0))
    if mode == "connection_refused":
        port = refused.getsockname()[1]

    def run_installation(*, baseline=False):
        location.mkdir()
        environment = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT", "WINDIR")
                       if name in os.environ}
        environment.update(PI_CODING_AGENT_DIR=str(location), PYTHONDEVMODE="1")
        command = [
            sys.executable, "-c", BOOTSTRAP, integration, outcome,
            f"http://127.0.0.1:{port}{install_telemetry.INSTALL_EVENTS_PATH}", str(location),
            "baseline" if baseline else "normal",
        ]
        with subprocess.Popen(command, cwd=ROOT, env=environment, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            if not baseline and mode != "connection_refused":
                assert collector.received.wait(5)
            stdout, stderr = process.communicate(timeout=5)
            if not baseline and mode == "timeout":
                assert not collector.disconnected.is_set()
        files = {p.relative_to(location): p.read_bytes()
                 for p in location.rglob("*") if p.is_file()}
        shutil.rmtree(location)
        return process.returncode, stdout, stderr, files

    try:
        without = run_installation(baseline=True)
        assert not collector.events
        assert without[0] == (0 if outcome == "success" else 2), without[2]
        assert run_installation() == without
    finally:
        refused.close()
    if mode == "timeout":
        assert collector.disconnected.wait(4), "the detached worker did not time out"
    if mode == "connection_refused":
        assert not collector.events
        return
    (path, event, authenticated), = collector.events
    assert path == "/openapi/v2/telemetry/install-events" and not authenticated
    assert event["event"] == "enterprise_install_finished"
    assert event["integration"] == integration and event["client"] == "pi"
    assert event["result"] == outcome and event["duration_ms"] >= 0
    assert set(event) <= {
        "event", "attempt_id", "installer_version", "integration", "client", "action",
        "result", "duration_ms", "failed_stage", "error_code", "region", "skill_status",
        "on_path", "cli_version",
    }
    assert str(location) not in json.dumps(event)
    if outcome == "failed":
        assert event["failed_stage"] == "resolve_client"
        assert event["error_code"] == "client_unresolved"
        assert "skill_status" not in event
        assert "cli_version" not in event and "on_path" not in event
        return
    if outcome == "partial":
        assert event["failed_stage"] == ("skill_install" if integration == "cli"
                                         else "mcp_config_write")
    if integration == "cli":
        assert event["cli_version"] == "0.8.0" and event["on_path"] is False
        assert "region" not in event
    else:
        assert event["region"] == "cn" and event["action"] == "install"


def test_worker_spawn_failure_is_isolated_and_attempted_once(monkeypatch):
    called = []

    def fail(*_args, **_kwargs):
        called.append(True)
        raise OSError("process launch failed")

    monkeypatch.setattr(install_telemetry.subprocess, "Popen", fail)
    install_telemetry.InstallTelemetry("cli", "pi").finish()
    assert called == [True]


@pytest.mark.parametrize(("changes", "action"), [
    (" + pixverse-platform-cli==0.8.0 (from file:///local/source)", "install"),
    (" ~ pixverse-platform-cli==0.8.0 (from file:///local/source)", "reinstall"),
    (" - pixverse-platform-cli==0.7.0\n + pixverse-platform-cli==0.8.0", "upgrade"),
    (" + dependency==1.0.0", "unknown"),
])
def test_cli_action_uses_uv_package_change(monkeypatch, changes, action):
    command = ["uv", "tool", "install"]
    result = subprocess.CompletedProcess(command, 0, "", changes)
    monkeypatch.setattr(install.subprocess, "run", lambda *_args, **_kwargs: result)
    report = install_telemetry.InstallTelemetry("cli", "pi")
    install.checked_run(command, "install", report=report)
    assert report.action == action
