"""默认安装 CLI 和当前客户端的共享 Skill；不配置 MCP、不调用业务 API。"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__:
    from . import install_skill
else:
    import install_skill

ROOT = Path(__file__).resolve().parents[1]


def checked_run(command, stage, timeout=240):
    """不回显安装器原始输出，避免包索引等配置中的认证信息进入报告。"""
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise ValueError(
            f"{stage}失败（退出码 {result.returncode}）。请检查安装环境，不要改写打包文件。"
        )
    return result.stdout.strip()


def install_cli():
    uv = shutil.which("uv")
    if not uv:
        raise ValueError(
            "需要 uv。安装说明：https://docs.astral.sh/uv/getting-started/installation/"
        )
    checked_run(
        [
            uv,
            "tool",
            "install",
            "--python",
            sys.executable,
            "--reinstall-package",
            "pixverse-platform-cli",
            str(ROOT),
        ],
        "CLI 隔离安装",
    )
    directory = checked_run([uv, "tool", "dir", "--bin"], "CLI 目录查询", timeout=15)
    binary = Path(directory).expanduser().resolve() / (
        "pixverse-api.exe" if os.name == "nt" else "pixverse-api"
    )
    if not binary.is_file():
        raise ValueError("uv 未返回可用的 pixverse-api 入口。")
    version = checked_run([str(binary), "--version"], "CLI 版本检查", timeout=20)
    checked_run([str(binary), "--help"], "CLI 帮助检查", timeout=20)
    executable_on_path = shutil.which("pixverse-api")
    return {
        "path": str(binary),
        "version": version,
        "help_verified": True,
        "on_path": bool(executable_on_path)
        and Path(executable_on_path).resolve() == binary.resolve(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=install_skill.CLIENTS, default="auto")
    parser.add_argument("--skills-dir", type=Path, help="显式覆盖当前客户端的 Skill 父目录。")
    parser.add_argument("--replace", action="store_true", help="先备份再替换不同版本的 Skill。")
    options = parser.parse_args()
    completed = {}
    try:
        # 安装脚本可在尚未安装项目的旧系统 Python 下运行。
        if sys.version_info < (3, 10):  # noqa: UP036
            raise ValueError("需要 Python 3.10 或更新版本。")
        target = install_skill.resolve_target(options.client, options.skills_dir)
        expected = install_skill.skill_files(install_skill.SOURCE)
        if not install_skill.REQUIRED <= expected.keys():
            raise ValueError("Skill 源文件不完整，请使用完整仓库。")
        destination = Path(target["skills_dir"]) / install_skill.NAME
        if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
            raise ValueError("目标必须是普通 Skill 目录。")
        if destination.exists() and not options.replace:
            if install_skill.skill_files(destination) != expected:
                raise ValueError("已有不同版本的 Skill；核对后使用 --replace，旧目录会先备份。")
        completed["cli"] = install_cli()
        completed["skill"] = install_skill.install(Path(target["skills_dir"]), options.replace)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        error = str(exc) if isinstance(exc, ValueError) else "安装进程失败或超时，请检查安装环境。"
        print(
            json.dumps({"ok": False, "error": error, "completed": completed}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2
    result = {
        "ok": True,
        **target,
        **completed,
        "mcp_configured": False,
        "skill_discovery": "requires_new_session_verification",
    }
    if not completed["cli"]["on_path"]:
        result["path_action_required"] = f"请将 {Path(completed['cli']['path']).parent} 加入 PATH。"
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
