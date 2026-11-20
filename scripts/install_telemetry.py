"""Report installation results without waiting for delivery."""

import json
import os
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

INSTALLER_VERSION = "0.1.0"
INSTALL_EVENTS_PATH = "/openapi/v2/telemetry/install-events"
ENDPOINTS = {
    "cn": f"https://app-api.pixverseai.cn{INSTALL_EVENTS_PATH}",
    "global": f"https://app-api.pixverse.ai{INSTALL_EVENTS_PATH}",
}
CLIENTS = {"workbuddy", "deepseek", "opencode", "pi"}
ACTIONS = ("install", "upgrade", "reinstall", "reconfigure", "noop")
WORKER_DEADLINE = 1.0


def cli_version(value):
    match = re.fullmatch(r"pixverse-api, version (\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]{1,24})?)",
                         value)
    return match[1] if match else None


class InstallTelemetry:
    def __init__(self, integration, client, region=None):
        self.started = time.monotonic()
        self.integration = integration
        self.client = client
        self.region = region
        self.action = "unknown"
        self.stage = "resolve_client"
        self.error_code = "client_unresolved"
        self.completed = {}
        self.success = False

    def step(self, stage, error_code):
        self.stage = stage
        self.error_code = error_code

    def finish(self):
        # The caller's result is already determined. A reporting failure is discarded.
        try:
            from uuid import uuid4

            result = "success" if self.success else ("partial" if self.completed else "failed")
            event = {
                "event": "enterprise_install_finished",
                "attempt_id": str(uuid4()),
                "installer_version": INSTALLER_VERSION,
                "integration": self.integration,
                "client": self.client if self.client in CLIENTS else "other",
                "action": self.action if self.action in ACTIONS else "unknown",
                "result": result,
                "duration_ms": int((time.monotonic() - self.started) * 1000),
            }
            if not self.success:
                event.update(failed_stage=self.stage, error_code=self.error_code)
            if self.region:
                event["region"] = self.region
            skill = self.completed.get("skill", {})
            if skill.get("status") in {"installed", "updated", "unchanged"}:
                event["skill_status"] = skill["status"]
            if cli := self.completed.get("cli"):
                if version := cli_version(cli["version"]):
                    event["cli_version"] = version
                event["on_path"] = cli["on_path"]
            detach = (
                {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt" else {"start_new_session": True}
            )
            environment = {name: os.environ[name] for name in ("SystemRoot", "WINDIR")
                           if os.name == "nt" and name in os.environ}
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ResourceWarning, module="subprocess")
                subprocess.Popen(
                    [sys.executable, "-IBS", str(Path(__file__).resolve()),
                     ENDPOINTS[self.region or "global"], json.dumps(event, separators=(",", ":"))],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    close_fds=True, env=environment, **detach,
                )
        except Exception:
            pass


def post_once(endpoint, payload):
    from http.client import HTTPConnection, HTTPException, HTTPSConnection
    from urllib.parse import urlsplit

    address = urlsplit(endpoint)
    if address.scheme == "https":
        connection_type = HTTPSConnection
    elif address.scheme == "http" and address.hostname == "127.0.0.1":
        connection_type = HTTPConnection
    else:
        return
    connection = connection_type(address.hostname, address.port, timeout=WORKER_DEADLINE)
    try:
        connection.request("POST", address.path, body=payload.encode("utf-8"),
                           headers={"Content-Type": "application/json"})
        with connection.getresponse():
            pass
    except (HTTPException, OSError, ValueError):
        pass
    finally:
        connection.close()


if __name__ == "__main__":
    # The deadline covers DNS as well as network I/O. The installer never joins this worker.
    from threading import Thread

    worker = Thread(target=post_once, args=sys.argv[1:], daemon=True)
    worker.start()
    worker.join(WORKER_DEADLINE)
