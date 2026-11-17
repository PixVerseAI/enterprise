"""识别当前客户端并安装完整 Skill；不处理凭据或 MCP 配置。"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

NAME = "pixverse-api"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / NAME
CLIENTS = ("auto", "workbuddy", "deepseek", "opencode", "pi")
REQUIRED = {Path("SKILL.md")} | {
    Path("references") / name for name in ("cli.md", "mcp.md", "showcase.md", "showcase.json")
}


def client_from_executable(executable):
    """只匹配可执行文件或 Node 入口，不从提示词和任意命令参数猜客户端。"""
    path = executable.replace("\\", "/").lower()
    name = path.rsplit("/", 1)[-1]
    if name in {"workbuddy", "codebuddy", "cbc", "codebuddy-lite-wb.mjs"}:
        return "workbuddy"
    if name == "dsh" or "/@deepseek-ai/dsh/" in path:
        return "deepseek"
    if name == "pi" or "/pi-coding-agent/" in path:
        return "pi"
    if name in {"opencode", "opencode.exe"}:
        return "opencode"
    return None


def process_identity(pid):
    """读取父进程编号和入口文件；不读取环境、认证文件或完整命令参数。"""
    proc = Path("/proc") / str(pid)
    if proc.is_dir():
        stat = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        parent = int(stat[1])
        executable = os.readlink(proc / "exe")
        client = client_from_executable(executable) or client_from_executable(
            (proc / "comm").read_text().strip()
        )
        if not client and Path(executable).name.lower() in {"node", "bun", "nodejs"}:
            # Node 的第二个 argv 是入口文件；不继续读取模型参数或用户提示词。
            with (proc / "cmdline").open("rb") as stream:
                arguments = []
                current = bytearray()
                for _ in range(8192):
                    byte = stream.read(1)
                    if not byte:
                        break
                    if byte == b"\0":
                        arguments.append(current.decode(errors="replace"))
                        current.clear()
                        if len(arguments) == 2:
                            break
                    else:
                        current.extend(byte)
            if arguments:
                client = client_from_executable(arguments[0])
            if not client and len(arguments) == 2 and not arguments[1].startswith("-"):
                client = client_from_executable(arguments[1])
        return parent, client
    # macOS 等无 /proc 的系统只查 comm，不读取带提示词或凭据的 command/args。
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "ppid=", "-o", "comm="],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    fields = result.stdout.strip().split(maxsplit=1)
    return (int(fields[0]), client_from_executable(fields[1])) if len(fields) == 2 else (0, None)


def detect_client(environment=None):
    """以实际父进程为准；多个已安装客户端的目录变量不代表当前客户端。"""
    pid = os.getppid()
    seen = set()
    for _ in range(24):
        if pid <= 1 or pid in seen:
            break
        seen.add(pid)
        try:
            pid, client = process_identity(pid)
        except (OSError, ValueError, subprocess.SubprocessError):
            break
        if client:
            return client, "parent_process"
    environment = os.environ if environment is None else environment
    markers = {
        "workbuddy": ("CODEBUDDY_CONFIG_DIR", "WORKBUDDY_CONFIG_DIR"),
        "deepseek": ("DSH_HOME",),
        "opencode": ("OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR"),
        "pi": ("PI_CODING_AGENT_DIR",),
    }
    candidates = [
        client
        for client, names in markers.items()
        if any(environment.get(name, "").strip() for name in names)
    ]
    if len(candidates) == 1:
        return candidates[0], "client_environment"
    raise ValueError(
        "无法唯一识别当前客户端。请根据正在使用的客户端传入 "
        "--client workbuddy|deepseek|opencode|pi；其他客户端使用 --skills-dir。"
    )


def client_skills_dir(client, environment=None, home=None):
    """返回该客户端的原生全局 Skill 父目录；模型配置目录不用于推导 Skill。"""
    environment = os.environ if environment is None else environment
    home = Path.home() if home is None else home

    def configured(name, default):
        value = environment.get(name, "").strip()
        return Path(value).expanduser() if value else default

    if client == "workbuddy":
        return configured("CODEBUDDY_CONFIG_DIR", home / ".codebuddy") / "skills"
    if client == "deepseek":
        return configured("DSH_HOME", home / ".dsh") / "skills"
    if client == "pi":
        return configured("PI_CODING_AGENT_DIR", home / ".pi" / "agent") / "skills"
    if client == "opencode":
        return configured("XDG_CONFIG_HOME", home / ".config") / "opencode" / "skills"
    raise ValueError("不支持的客户端；请使用 --skills-dir 指定原生 Skill 父目录。")


def resolve_target(client="auto", skills_dir=None):
    if skills_dir is not None:
        return {
            "client": client if client != "auto" else "custom",
            "detected_by": "explicit_path",
            "skills_dir": str(skills_dir.expanduser().resolve()),
        }
    if client == "auto":
        client, evidence = detect_client()
    else:
        evidence = "explicit_client"
    return {
        "client": client,
        "detected_by": evidence,
        "skills_dir": str(client_skills_dir(client).expanduser().resolve()),
    }


def skill_files(directory):
    """只接受独立 Skill 目录内的普通文件，不跟随符号链接。"""
    result = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("Skill 目录包含符号链接，请先核对安装来源。")
        if path.is_file():
            result[path.relative_to(directory)] = path.read_bytes()
    return result


def install(skills_dir, replace=False):
    expected = skill_files(SOURCE)
    if not REQUIRED <= expected.keys():
        raise ValueError("全局 Skill 源文件不完整。请使用完整的仓库目录。")
    parent = skills_dir.expanduser().resolve()
    target = parent / NAME
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise ValueError("目标必须是普通 Skill 目录。")
    if target.exists():
        if skill_files(target) == expected:
            return {"ok": True, "status": "unchanged", "name": NAME, "skill_dir": str(target)}
        if not replace:
            raise ValueError("已有不同版本。核对目标后使用 --replace；旧目录会先备份。")
    parent.mkdir(parents=True, exist_ok=True)
    backup = None
    with tempfile.TemporaryDirectory(prefix=".pixverse-api-install-", dir=parent) as temporary:
        staged = Path(temporary) / NAME
        shutil.copytree(SOURCE, staged)
        if skill_files(staged) != expected:
            raise ValueError("复制后的 Skill 与源文件不一致，已停止安装。")
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            # 备份放在 Skill 父目录之外，避免被客户端重新发现为同名 Skill。
            backup_root = parent.parent / f".{parent.name}-pixverse-api-backups"
            backup_root.mkdir(parents=True, exist_ok=True)
            backup = backup_root / f"{stamp}-{uuid4().hex[:8]}"
            target.rename(backup)
        try:
            staged.rename(target)
        except OSError:
            if backup is not None:
                backup.rename(target)
            raise
    result = {
        "ok": True,
        "status": "updated" if backup else "installed",
        "name": NAME,
        "skill_dir": str(target),
    }
    if backup is not None:
        result["backup_dir"] = str(backup)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="覆盖当前客户端的 Skill 父目录；不同时修改其他客户端。",
    )
    parser.add_argument("--client", choices=CLIENTS, default="auto", help="默认识别当前 Agent。")
    parser.add_argument("--detect", action="store_true", help="只报告客户端和目标目录，不安装。")
    parser.add_argument("--replace", action="store_true", help="备份并替换已有不同版本。")
    options = parser.parse_args()
    try:
        target = resolve_target(options.client, options.skills_dir)
        result = (
            {"ok": True, **target}
            if options.detect
            else {
                **install(Path(target["skills_dir"]), options.replace),
                **target,
                "discovery": "requires_new_session_verification",
            }
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
