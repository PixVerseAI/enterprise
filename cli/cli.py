"""一次性命令；所有网络能力显式调用，无持久凭据或隐式任务状态。"""

import json
import math
import os
import sys
from functools import partial, wraps

import click

from . import __version__
from .catalog import register_catalog
from .client import APIError, PlatformClient, redact
from .config import Config, ConfigurationError
from .execution import execute_operation, failure_context
from .protocol import InputError
from .workflows import register_workflows, webhook


class CommandError(click.ClickException):
    def __init__(self, error, json_output):
        super().__init__(error["message"])
        self.error = {"stage": "validation", "submission_state": "not_submitted", **error}
        self.json_output = json_output
        self.exit_code = 2 if error["type"] in ("configuration", "validation") else 1

    def show(self, file=None):
        if self.json_output:
            click.echo(json.dumps({"ok": False, "stage": self.error["stage"],
                                   "submission_state": self.error["submission_state"],
                                   "error": self.error}, ensure_ascii=False), err=True)
        else:
            click.echo(f"错误：{self.message}", err=True)
            if self.error.get("trace_id"):
                click.echo(f"Trace ID：{self.error['trace_id']}", err=True)
            if self.error.get("response"):
                click.echo(
                    json.dumps(self.error["response"], ensure_ascii=False, indent=2), err=True
                )


def action(fn):
    """将命令行输入输出与业务执行分开。"""

    @wraps(fn)
    @click.pass_context
    def wrapped(ctx, **kwargs):
        options = ctx.find_root().obj
        name = f"{ctx.parent.command.name}_{ctx.command.name.replace('-', '_')}"
        try:
            config = Config.from_env(region=options["region"])
            result = execute_operation(
                fn, config, kwargs, name=name, timeout=options["timeout"],
                client_factory=PlatformClient
            )
        except APIError as exc:
            raise CommandError(exc.as_dict(), options["json"]) from None
        except ConfigurationError as exc:
            raise CommandError(
                {"type": "configuration", "message": str(exc), **failure_context(name)},
                options["json"]
            ) from None
        except InputError as exc:
            raise CommandError({**failure_context(name), **exc.detail}, options["json"]) from None
        except (ValueError, OSError) as exc:
            # 不回显原始环境变量、URL、路径或用户输入。
            message = (
                str(exc) if isinstance(exc, ValueError) else "本地文件无法读取，请检查路径和权限。"
            )
            raise CommandError(
                {"type": "validation", "message": message, **failure_context(name)}, options["json"]
            ) from None
        if result.get("submission") == "accepted":
            query = result.get("query_command")
            if not query:
                query = f"video get --id {result['response']['Resp']['video_id']}"
            result["query_command"] = f"pixverse-api --region {config.region} --json {query}"
        failed = result.get("task_status") in ("moderation_failed", "failed")
        if options["json"]:
            click.echo(json.dumps({"ok": not failed, **result}, ensure_ascii=False))
        else:
            click.echo(
                f"地区：{result['region']}  环境：production  Trace ID：{result['trace_id']}"
            )
            if result.get("submission") == "accepted":
                query = result.get("query_command", "video get")
                click.echo(f"任务已提交；尚未确认生成完成。使用 {query} 查询。")
            if "task_status" in result:
                click.echo(f"任务状态：{result['task_status']}（未探测成片 URL）")
            click.echo(json.dumps(result["response"], ensure_ascii=False, indent=2))
        if failed:
            ctx.exit(1)

    return wrapped


@click.group(name="pixverse-api", context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--region", type=click.Choice(["global", "cn"]), default="global", show_default=True,
    help="选择生产 API 地区；不读取地区环境变量。",
)
@click.option("--json", "json_output", is_flag=True, help="stdout 输出 JSON，失败信息写入 stderr。")
@click.option(
    "--timeout",
    type=click.FloatRange(min=0.1),
    default=60.0,
    show_default=True,
    help="单次 HTTP 操作超时秒数；不自动重试。",
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx, region, json_output, timeout):
    """统一的国内/海外 Platform CLI，仅连接生产 API。

    先设置 PIXVERSE_API_KEY；使用 --region 选择地区，默认 global。
    """
    if not math.isfinite(timeout):
        raise click.BadParameter("必须是有限正数。", param_hint="--timeout")
    ctx.obj = {"region": region, "json": json_output, "timeout": timeout}


@cli.group()
def account():
    """查询账号信息。"""


@account.command()
@action
def balance(client):
    """查询当前地区、当前 Key 对应账号的点数余额。"""
    return client.balance()


def upload_options(fn):
    fn = click.option("--url", help="公网资源 URL，与 --file 二选一。")(fn)
    return click.option("--file", type=click.Path(path_type=str), help="本地文件路径。")(fn)


@cli.group()
def image():
    """图片素材。"""


@image.command("upload")
@upload_options
@action
def upload_image(client, file, url):
    """上传图片，返回 img_id（文件或 URL）。"""
    return client.upload("image", file=file, url=url)


@cli.group()
def media():
    """视频、音频素材。"""


@media.command("upload")
@upload_options
@action
def upload_media(client, file, url):
    """上传视频或音频，返回 media_id（文件或 URL）。"""
    return client.upload("media", file=file, url=url)


@cli.group()
def video():
    """创建视频任务或查询已有任务。"""


def generation_options(fn, *, prompt_required=True):
    for option in [
        click.option("--prompt", required=prompt_required, help="正向提示词，最多 5000 个字符。"),
        click.option(
            "--model", default="v6", show_default=True, help="模型名称；可用性由服务端校验。"
        ),
        click.option("--duration", type=click.IntRange(min=1), default=5, show_default=True),
        click.option(
            "--quality",
            type=click.Choice(["360p", "540p", "720p", "1080p"]),
            default="720p",
            show_default=True,
        ),
        click.option("--seed", type=click.IntRange(0, 2147483647)),
        click.option("--negative-prompt", help="反向提示词；具体模型支持由服务端校验。"),
        click.option("--webhook-id", help="同账号的正整数字符串 Webhook ID。"),
        click.option("--audio/--no-audio", default=None, help="是否生成音频；省略使用服务端默认。"),
        click.option(
            "--multi-clip/--no-multi-clip", default=None, help="多镜头开关；依赖模型支持。"
        ),
    ]:
        fn = option(fn)
    return fn


def generation_payload(
    prompt, model, duration, quality, seed, audio, multi_clip, negative_prompt=None, webhook_id=None
):
    """构造基础生成载荷，保留可选字段的省略与显式false。"""
    payload = dict(prompt=prompt, model=model, duration=duration, quality=quality)
    if prompt is None:
        payload.pop("prompt")
    for key, value in [
        ("seed", seed),
        ("generate_audio_switch", audio),
        ("generate_multi_clip_switch", multi_clip),
        ("negative_prompt", negative_prompt),
    ]:
        if value is not None:
            payload[key] = value
    return {**payload, **webhook(webhook_id)}


@video.command("generate")
@generation_options
@click.option(
    "--aspect-ratio",
    default="16:9",
    show_default=True,
    type=click.Choice(["16:9", "9:16", "4:3", "3:4", "1:1", "2:3", "3:2", "21:9"]),
)
@action
def text_to_video(client, aspect_ratio, **kwargs):
    """文生视频：提交一次任务，返回 video_id，不自动查询或重试。"""
    return client.generate({**generation_payload(**kwargs), "aspect_ratio": aspect_ratio})


@video.command("from-image")
@partial(generation_options, prompt_required=False)
@click.option(
    "--img-id", required=True, type=click.IntRange(min=1), help="同地区、同账号上传的 img_id。"
)
@action
def image_to_video(client, img_id, **kwargs):
    """单图生视频：提示词可选，画幅沿用图片，提交一次后返回 video_id。"""
    return client.generate({**generation_payload(**kwargs), "img_id": img_id}, image=True)


@video.command("get")
@click.option("--id", "video_id", required=True, type=click.IntRange(min=1), help="已有 video_id。")
@action
def get_video(client, video_id):
    """查询一次视频任务；失败/拒审终态退出码为 1。"""
    return client.task(video_id)


register_workflows(cli, video, media, action)
register_catalog(cli, account, action)


def main():
    try:
        code = cli(standalone_mode=False)
        if isinstance(code, int):
            sys.exit(code)
    except click.ClickException as exc:
        # Click 参数错误也避免将可能误填的 Key/URL 直接回显。
        key = os.environ.get("PIXVERSE_API_KEY", "")
        if not isinstance(exc, CommandError):
            detail = {"type": "validation", "message": redact(exc.message, key),
                      "code": "INVALID_ARGUMENT", "fields": []}
            context = getattr(exc, "ctx", None)
            if context is not None and context.parent is not None:
                name = f"{context.parent.command.name}_{context.command.name.replace('-', '_')}"
                detail.update(failure_context(name))
            parameter = getattr(exc, "param", None)
            if parameter is not None:
                detail["fields"] = [parameter.name]
                if isinstance(exc, click.MissingParameter):
                    detail["code"] = "FIELD_REQUIRED"
                elif isinstance(parameter.type, click.Choice):
                    detail.update(code="FIELD_ENUM", allowed_values=list(parameter.type.choices))
            exc = CommandError(
                detail,
                "--json" in sys.argv,
            )
        exc.show()
        sys.exit(exc.exit_code)
    except click.Abort:
        click.echo("操作已中断；如已发送写请求，请核查任务后再决定是否重新提交。", err=True)
        sys.exit(130)
