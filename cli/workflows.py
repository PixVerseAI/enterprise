"""公开生成场景的共享命令与请求构造；不调用内部工作流接口。"""

import re
from pathlib import Path
from urllib.parse import quote

import click

from .client import APIError
from .protocol import json_object

ID = click.IntRange(1, 2**64 - 1)
SEED = click.IntRange(0, 2147483647)
QUALITIES = ["360p", "540p", "720p", "1080p"]
RATIOS = ["16:9", "9:16", "4:3", "3:4", "1:1", "2:3", "3:2", "21:9"]
LANGUAGES = (
    "en-AU pt-BR es-BR en-CA fr-CA zh-CN es-CO fr-FR de-DE hi-IN en-IN id-ID it-IT ja-JP "
    "ms-MY es-MX nl-NL en-NL fil-PH en-PH pl-PL ru-RU en-SG ko-KR es-ES de-CH fr-CH it-CH "
    "zh-TW th-TH en-TH tr-TR ar-AE en-AE en-GB en-US es-US vi-VN"
).split()


def opt(name, **kwargs):
    return ((name,), kwargs)


def options(*specs):
    def decorate(fn):
        for names, kwargs in reversed(specs):
            fn = click.option(*names, **kwargs)(fn)
        return fn

    return decorate


def quality(values=QUALITIES, default="720p"):
    return opt("--quality", type=click.Choice(values), default=default, show_default=True)


def aspect(values=RATIOS, default="16:9"):
    return opt("--aspect-ratio", type=click.Choice(values), default=default, show_default=True)


SOURCE = [opt("--source-video-id", type=ID), opt("--video-media-id", type=ID)]
WEBHOOK = opt("--webhook-id", help="同账号的数字字符串 Webhook ID。")
SEED_OPTION = opt("--seed", type=SEED)
VOICE = [opt("--audio-media-id", type=ID), opt("--tts-speaker-id"), opt("--tts-content")]
GENERATION = [
    opt("--prompt", required=True),
    opt("--model", default="v6", show_default=True),
    opt("--duration", type=click.IntRange(1), default=5, show_default=True),
    quality(),
    SEED_OPTION,
    opt("--negative-prompt"),
    opt("--audio/--no-audio", default=None),
    WEBHOOK,
]


def text(value, name, maximum=None, required=True):
    if value is None and not required:
        return
    if (not isinstance(value, str) or (required and not value.strip())
            or maximum is not None and len(value) > maximum):
        raise ValueError(f"{name} 内容为空或超过允许长度 {maximum}。")


def compact(values):
    # False、0 必须保留；未指定的选项不覆盖服务端默认值。
    return {key: value for key, value in values.items() if value is not None}


def source(source_video_id, video_media_id):
    if (source_video_id is None) == (video_media_id is None):
        raise ValueError("--source-video-id 和 --video-media-id 必须且只能提供一个。")
    return compact(dict(source_video_id=source_video_id, video_media_id=video_media_id))


def webhook(value):
    if value is not None and (not value.isascii() or not value.isdecimal() or int(value) < 1):
        raise ValueError("--webhook-id 必须是正整数字符串。")
    return compact({"webhook_id": value})


def voice(audio_media_id, tts_speaker_id, tts_content):
    has_tts = tts_speaker_id is not None or tts_content is not None
    if (audio_media_id is not None) == has_tts:
        raise ValueError("音频 ID 与 TTS 参数组必须且只能选择一种。")
    if audio_media_id is not None:
        return {"audio_media_id": audio_media_id}
    return {"lip_sync_tts_speaker_id": tts_speaker_id, "lip_sync_tts_content": tts_content}


def custom_voice_id(value):
    """只允许自定义音色标识，避免误删系统音色或拼入其他请求路径。"""
    if not isinstance(value, str) or not re.match(r"(?i)^custom_", value):
        raise ValueError("speaker-id 必须是创建响应中的custom_自定义音色ID。")
    return value


def generation(prompt, model, duration, quality, seed, negative_prompt, audio, webhook_id):
    return {
        **compact(
            dict(
                prompt=prompt,
                model=model,
                duration=duration,
                quality=quality,
                seed=seed,
                negative_prompt=negative_prompt,
                generate_audio_switch=audio,
            )
        ),
        **webhook(webhook_id),
    }


def reference(raw, kind):
    item = json_object(raw)
    allowed = (
        {"img_id", "type", "ref_name"}
        if kind == "image"
        else {"source_video_id", "video_media_id", "ref_name"}
    )
    if not isinstance(item, dict) or not item or set(item) - allowed:
        raise ValueError("引用对象包含不支持的字段。")
    ids = ("img_id",) if kind == "image" else ("source_video_id", "video_media_id")
    if sum(key in item for key in ids) != 1:
        raise ValueError("每个引用必须包含且仅包含一个正确类型的资源 ID。")
    for key in ids:
        if key in item and (type(item[key]) is not int or not 1 <= item[key] < 2**64):
            raise ValueError("引用资源 ID 必须为正整数，不能是字符串或布尔值。")
    return item


def lyric_timestamp(filename):
    """读取公开歌词对象；顺序、文字及实际音频匹配由 Platform 校验。"""
    return filename if isinstance(filename, dict) else json_object(
        Path(filename).read_text(encoding="utf-8")
    )


def transition_frames(values):
    """保留有序帧和显式值，模型对应的分段范围由 Platform 校验。"""
    return [json_object(raw) for raw in values]


def register_workflows(root, video, media, action):
    @video.command("sound-effect")
    @options(
        *SOURCE,
        opt("--sound-effect-content"),
        opt("--original-sound/--no-original-sound", default=None),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def sound_effect(
        client,
        source_video_id,
        video_media_id,
        sound_effect_content,
        original_sound,
        seed,
        webhook_id,
    ):
        """给已有视频生成音效，可显式保留或关闭原声。"""
        text(sound_effect_content, "sound-effect-content", maximum=2048, required=False)
        return client.submit(
            "video/sound_effect/generate",
            {
                **source(source_video_id, video_media_id),
                **compact(
                    dict(
                        sound_effect_content=sound_effect_content,
                        original_sound_switch=original_sound,
                        seed=seed,
                    )
                ),
                **webhook(webhook_id),
            },
        )

    @video.command("multi-transition")
    @options(
        opt(
            "--frame",
            multiple=True,
            required=True,
            help='按顺序重复传JSON，如 {"img_id":123,"duration":5,"prompt":"sunset"}。',
        ),
        opt("--model", default="v5", show_default=True),
        quality(),
        opt("--motion-mode", type=click.Choice(["normal", "fast"]), default="normal"),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def multi_transition(client, frame, model, quality, motion_mode, seed, webhook_id):
        """至少两张关键帧依次转场；分段及总时长由 Platform 校验。"""
        return client.submit(
            "video/multi_transition/generate",
            {
                "multi_transition": transition_frames(frame),
                "model": model,
                "quality": quality,
                "motion_mode": motion_mode,
                **compact(dict(seed=seed)),
                **webhook(webhook_id),
            },
        )

    @video.command("f2v")
    @options(
        *GENERATION,
        opt("--first-frame-img", required=True, type=ID),
        opt("--last-frame-img", required=True, type=ID),
    )
    @action
    def f2v(client, first_frame_img, last_frame_img, **kwargs):
        """首尾帧生成：两张已上传图片之间生成视频。"""
        return client.submit(
            "video/transition/generate",
            {
                **generation(**kwargs),
                "first_frame_img": first_frame_img,
                "last_frame_img": last_frame_img,
            },
        )

    @video.command("fusion")
    @options(
        *[s for s in GENERATION if s[0] != ("--duration",)],
        opt("--duration", type=click.IntRange(0), default=None),
        aspect(RATIOS + ["auto"]),
        opt("--img-id", type=ID, multiple=True),
        opt(
            "--image-ref",
            multiple=True,
            help='重复传 JSON 对象，如 {"img_id":123,"ref_name":"dog"}。',
        ),
        opt("--video-ref", multiple=True, help="重复传 JSON 视频引用对象。"),
        opt("--reference-mode", type=click.Choice(["omni"])),
    )
    @action
    def fusion(client, img_id, image_ref, video_ref, reference_mode, aspect_ratio, **kwargs):
        """Combine image references, or images and videos with V6 Omni.
        For a role-specific request, give each referenced asset a ref_name with
        --image-ref or --video-ref. End each @name with a space or the end of
        the prompt. For example, use --prompt '@person wears @jacket and walks along @trail'
        """
        if img_id and image_ref:
            raise ValueError("--img-id 和 --image-ref 不可同时使用。")
        images = [reference(raw, "image") for raw in image_ref] or [{"img_id": i} for i in img_id]
        videos = [reference(raw, "video") for raw in video_ref]
        if not images and not videos:
            raise ValueError("Fusion 至少需要一个图片或视频引用。")
        return client.submit(
            "video/fusion/generate",
            {
                **generation(**kwargs),
                "aspect_ratio": aspect_ratio,
                **compact(
                    {
                        "image_references": images or None,
                        "video_references": videos or None,
                        "reference_mode": reference_mode,
                    }
                ),
            },
        )

    @video.command("extend")
    @options(*GENERATION, *SOURCE)
    @action
    def extend(client, source_video_id, video_media_id, **kwargs):
        """延长源视频时间。"""
        return client.submit(
            "video/extend/generate",
            {**source(source_video_id, video_media_id), **generation(**kwargs)},
        )

    @video.command("expand")
    @options(
        *SOURCE,
        opt("--aspect-ratio", required=True, help="目标画幅，包括接口支持的自定义比例。"),
        quality(["720p", "1080p"]),
    )
    @action
    def expand(client, source_video_id, video_media_id, aspect_ratio, quality):
        """扩展画面边界；独立于视频延长。"""
        return client.submit(
            "video/expand/generate",
            {
                **source(source_video_id, video_media_id),
                "aspect_ratio": aspect_ratio,
                "quality": quality,
            },
        )

    @video.command("upscale")
    @options(*SOURCE, SEED_OPTION, WEBHOOK)
    @action
    def upscale(client, source_video_id, video_media_id, seed, webhook_id):
        """视频超分。"""
        return client.submit(
            "video/upscale/generate",
            {
                **source(source_video_id, video_media_id),
                **compact({"seed": seed}),
                **webhook(webhook_id),
            },
        )

    @video.command("restyle")
    @options(
        *SOURCE,
        opt("--restyle-id", type=ID),
        opt("--restyle-prompt"),
        opt("--negative-prompt"),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def restyle(
        client,
        source_video_id,
        video_media_id,
        restyle_id,
        restyle_prompt,
        negative_prompt,
        seed,
        webhook_id,
    ):
        """预设风格或提示词重绘，两个风格来源二选一。"""
        return client.submit(
            "video/restyle/generate",
            {
                **source(source_video_id, video_media_id),
                **webhook(webhook_id),
                **compact(
                    dict(
                        restyle_id=restyle_id,
                        restyle_prompt=restyle_prompt,
                        negative_prompt=negative_prompt,
                        seed=seed,
                    )
                ),
            },
        )

    @video.command("lipsync")
    @options(*SOURCE, *VOICE, WEBHOOK)
    @action
    def lipsync(client, source_video_id, video_media_id, webhook_id, **kwargs):
        """源视频配音频或TTS对口型。"""
        return client.submit(
            "video/lip_sync/generate",
            {**source(source_video_id, video_media_id), **voice(**kwargs), **webhook(webhook_id)},
        )

    @video.command("avatar")
    @options(
        opt("--img-id", required=True, type=ID),
        *VOICE,
        quality(),
        opt("--prompt"),
        WEBHOOK,
    )
    @action
    def avatar(client, img_id, quality, prompt, webhook_id, **kwargs):
        """图片数字人：图片配音频或TTS。"""
        return client.submit(
            "video/avatar/generate",
            {
                "img_id": img_id,
                "quality": quality,
                **compact({"prompt": prompt}),
                **voice(**kwargs),
                **webhook(webhook_id),
            },
        )

    @video.command("mimic")
    @options(
        *SOURCE,
        opt("--img-id", required=True, type=ID),
        quality(QUALITIES[:3]),
        opt("--post-reference", type=click.Choice(["image", "video"])),
        WEBHOOK,
    )
    @action
    def mimic(client, source_video_id, video_media_id, img_id, quality, post_reference, webhook_id):
        """图片主体模仿视频动作；post-reference 控制姿态参考。"""
        return client.submit(
            "video/mimic/generate",
            {
                **source(source_video_id, video_media_id),
                "img_id": img_id,
                "quality": quality,
                **compact({"post_reference": post_reference}),
                **webhook(webhook_id),
            },
        )

    @video.command("mask")
    @options(*SOURCE, opt("--keyframe-id", type=click.IntRange(0)))
    @action
    def mask(client, source_video_id, video_media_id, keyframe_id):
        """同步获取Mask与关键帧，不自动选择或提交后续任务。"""
        return client.request(
            "POST",
            "/openapi/v2/video/mask/selection",
            json={**source(source_video_id, video_media_id),
                  **compact({"keyframe_id": keyframe_id})},
        )

    @video.command("swap")
    @options(
        *SOURCE,
        opt("--keyframe-id", required=True, type=click.IntRange(0)),
        opt("--mask-id", required=True),
        opt("--img-id", required=True, type=ID),
        quality(QUALITIES[:3], "540p"),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def swap(
        client,
        source_video_id,
        video_media_id,
        keyframe_id,
        mask_id,
        img_id,
        quality,
        seed,
        webhook_id,
    ):
        """替换主体：Mask ID保持字符串，视频/关键帧须来自同一次Mask请求。"""
        return client.submit(
            "video/swap/generate",
            {
                **source(source_video_id, video_media_id),
                "keyframe_id": keyframe_id,
                "mask_id": mask_id,
                "img_id": img_id,
                "quality": quality,
                **compact({"seed": seed}),
                **webhook(webhook_id),
            },
        )

    @video.command("modify")
    @options(
        *SOURCE,
        opt("--prompt", required=True),
        opt("--img-id", type=ID, multiple=True),
        opt("--mask-id", multiple=True),
        opt("--mask-url", multiple=True),
        opt("--keyframe-id", type=click.IntRange(0)),
        quality(QUALITIES[:3], "540p"),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def modify(
        client,
        source_video_id,
        video_media_id,
        prompt,
        img_id,
        mask_id,
        mask_url,
        keyframe_id,
        quality,
        seed,
        webhook_id,
    ):
        """整体/局部修改；重复传图片或Mask选项以保持引用顺序。"""
        text(prompt, "prompt")
        if mask_id and mask_url:
            raise ValueError("mask-id 与 mask-url 不能混用。")
        if mask_id and keyframe_id is None:
            raise ValueError("使用 mask-id 时必须显式提供 keyframe-id。")
        return client.submit(
            "video/modify/generate",
            {
                **source(source_video_id, video_media_id),
                "prompt": prompt,
                "quality": quality,
                **compact(
                    dict(
                        img_ids=list(img_id) or None,
                        mask_ids=list(mask_id) or None,
                        mask_urls=list(mask_url) or None,
                        keyframe_id=keyframe_id,
                        seed=seed,
                    )
                ),
                **webhook(webhook_id),
            },
        )

    @video.command("restyle-list")
    @options(
        opt("--page", type=click.IntRange(1), default=1),
        opt("--page-size", type=click.IntRange(1, 500), default=50),
    )
    @action
    def restyle_list(client, page, page_size):
        """查询预设重绘风格。"""
        return client.request(
            "GET",
            "/openapi/v2/video/restyle/list",
            params={"page_num": page, "page_size": page_size},
        )

    @root.group("voice")
    def voice_group():
        """系统/自定义音色查询，以及自定义音色创建和删除。"""

    @voice_group.command("list")
    @options(
        opt("--page", type=click.IntRange(1), default=1),
        opt("--page-size", type=click.Choice(["10", "20", "50", "100"]), default="20"),
        (("--type", "speaker_type"), {"type": click.Choice(["system", "custom", "all"]),
                                    "default": "all"}),
        opt("--scene", type=click.Choice(["avatar", "lip_sync"])),
    )
    @action
    def voice_list(client, page, page_size, speaker_type, scene):
        """默认查询系统及自定义音色，每页20条；不自动翻页。"""
        return client.request(
            "GET",
            "/openapi/v2/video/tts_speaker",
            params={
                "page_num": page,
                "page_size": page_size,
                **compact({"speaker_type": speaker_type, "scene": scene}),
            },
        )

    @voice_group.command("create")
    @options(opt("--name", required=True), opt("--audio-media-id", type=ID, required=True))
    @action
    def voice_create(client, name, audio_media_id):
        """由同账号上传音频创建自定义音色；音频最长30秒由服务端校验。"""
        text(name, "name", maximum=128)
        result = client.request(
            "POST",
            "/openapi/v2/video/tts_speaker",
            json={"name": name, "audio_media_id": audio_media_id},
        )
        try:
            speaker_id = result["response"]["Resp"].get("speaker_id")
            if not isinstance(speaker_id, str) or not speaker_id.strip():
                raise ValueError("缺少音色 ID。")
            result["speaker_id"] = speaker_id
        except ValueError:
            raise APIError(
                "protocol",
                "创建响应缺少有效自定义speaker_id，请核查列表后再决定是否重试。",
                trace_id=result["trace_id"],
                http_status=result["http_status"],
                response=result["response"],
            ) from None
        return result

    @voice_group.command("delete")
    @options(opt("--speaker-id", required=True))
    @action
    def voice_delete(client, speaker_id):
        """仅删除明确指定的自定义音色；保持服务端空Resp协议。"""
        speaker_id = custom_voice_id(speaker_id)
        encoded = quote(speaker_id, safe="").replace(".", "%2E")
        return client.request(
            "DELETE", f"/openapi/v2/video/tts_speaker/{encoded}",
            allow_empty_resp=True
        )

    register_agents(root, action)


def register_agents(root, action):
    @root.group()
    def agent():
        """电商Native/Template和最新统一V3 MV。"""

    ecommerce_options = [
        opt("--img-id", type=ID, multiple=True),
        opt("--image-ref", multiple=True, help="重复传JSON图片引用，保留img_id/ref_name。"),
        opt("--prompt", required=True),
        opt("--duration", type=click.Choice(["15", "30", "45", "60"]), required=True),
        opt("--language-code", required=True, type=click.Choice(LANGUAGES)),
        quality(["720p", "1080p"]),
        aspect(RATIOS[:5] + ["21:9"], "9:16"),
        opt("--avatar"),
        opt("--lip-sync/--no-lip-sync", default=None),
        opt("--bgm/--no-bgm", default=None),
        opt("--caption/--no-caption", default=None),
        WEBHOOK,
    ]

    def ecommerce(
        client,
        agent_id,
        img_id,
        image_ref,
        prompt,
        duration,
        language_code,
        quality,
        aspect_ratio,
        avatar,
        lip_sync,
        bgm,
        caption,
        webhook_id,
        video_style=None,
    ):
        text(prompt, "prompt")
        if img_id and image_ref:
            raise ValueError("--img-id 和 --image-ref 不可同时使用。")
        images = [reference(raw, "image") for raw in image_ref] or [{"img_id": i} for i in img_id]
        if any(set(item) - {"img_id", "ref_name"} for item in images):
            raise ValueError("电商图片引用只支持 img_id 和 ref_name。")
        if isinstance(avatar, str) and avatar.lower() == "auto":
            avatar = "Auto"
        return client.submit(
            "video/agent/generate",
            {
                "agent_id": agent_id,
                "img_references": images,
                "prompt": prompt,
                "duration": int(duration),
                "language_code": language_code,
                "quality": quality,
                "aspect_ratio": aspect_ratio,
                **compact(
                    dict(
                        avatar=avatar,
                        video_style=video_style,
                        lip_sync_switch=lip_sync,
                        bgm_switch=bgm,
                        caption_switch=caption,
                    )
                ),
                **webhook(webhook_id),
            },
        )

    @agent.command("ecommerce-native")
    @options(*ecommerce_options)
    @action
    def ecommerce_native(client, **kwargs):
        """电商Native，固定agent_id=414562414124107。"""
        return ecommerce(client, 414562414124107, **kwargs)

    @agent.command("ecommerce-template")
    @options(
        *ecommerce_options,
        opt(
            "--video-style",
            required=True,
            type=click.Choice(["polished_commercials", "personal_review", "no_personal_review"]),
        ),
    )
    @action
    def ecommerce_template(client, **kwargs):
        """电商Template，固定agent_id=414562414124108。"""
        return ecommerce(client, 414562414124108, **kwargs)

    @agent.command("mv")
    @options(
        opt("--audio-media-id", type=ID, required=True),
        opt("--img-id", type=ID),
        opt("--style-img-id", type=ID),
        quality(["720p", "1080p"]),
        aspect(RATIOS[:5]),
        opt("--mv-style", help="可用风格由服务端模板校验，支持Custom、auto等。"),
        opt("--music-style"),
        opt("--mv-prompt"),
        opt("--lyric-text"),
        opt("--lyric-timestamp-file", type=click.Path()),
        opt("--caption/--no-caption", default=None),
        opt("--lip-sync/--no-lip-sync", default=None),
        opt("--preserve-outfit/--no-preserve-outfit", default=None),
        SEED_OPTION,
        WEBHOOK,
    )
    @action
    def mv(
        client,
        audio_media_id,
        img_id,
        style_img_id,
        quality,
        aspect_ratio,
        mv_style,
        music_style,
        mv_prompt,
        lyric_text,
        lyric_timestamp_file,
        caption,
        lip_sync,
        preserve_outfit,
        seed,
        webhook_id,
    ):
        """统一V3 MV：固定vibe_mv_v3_custom，由服务端异步校验音频。"""
        for name, value in [
            ("mv-style", mv_style),
            ("music-style", music_style),
            ("mv-prompt", mv_prompt),
            ("lyric-text", lyric_text),
        ]:
            text(value, name, required=False)
        custom = mv_style is not None and mv_style.strip().lower() == "custom"
        if custom and img_id is None and style_img_id is None:
            raise ValueError("Custom风格至少需要角色图或风格图。")
        if style_img_id is not None and not custom:
            raise ValueError("style-img-id 仅可用于 mv-style=Custom。")
        lyric = lyric_timestamp(lyric_timestamp_file) if lyric_timestamp_file else None
        return client.submit(
            "video/music_mv_agent/generate",
            {
                "mv_agent_type": "vibe_mv_v3_custom",
                "audio_media_id": audio_media_id,
                "quality": quality,
                "aspect_ratio": aspect_ratio,
                **compact(
                    dict(
                        image_references=[{"img_id": img_id}] if img_id else None,
                        style_img_references=[{"img_id": style_img_id}] if style_img_id else None,
                        mv_style=mv_style,
                        music_style=music_style,
                        mv_prompt=mv_prompt,
                        lyric_text=lyric_text,
                        lyric_timestamp=lyric,
                        caption_switch=caption,
                        lip_sync_switch=lip_sync,
                        preserve_outfit=preserve_outfit,
                        seed=seed,
                    )
                ),
                **webhook(webhook_id),
            },
        )
