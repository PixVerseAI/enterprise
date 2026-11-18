---
name: pixverse-api-cli
description: Use the pixverse-api CLI to upload assets, query balances, generate and edit videos, and run ecommerce Native/Template and unified V3 MV on the selected production Platform API.
---

# PixVerse API CLI

This file is the command guide bundled with the CLI package. The repository's shared `pixverse-api` skill provides business guidance for both CLI and MCP. When installing a skill for an AI assistant, install the complete shared skill directory, including its references.

Use the installed `pixverse-api`. The root option `--region global|cn` selects the production API and defaults to `global`; the CLI does not read a region environment variable. Supply the API key only through `PIXVERSE_OPENAPI_KEY`. Users configure credentials in their runtime environment. Do not read authentication files, print keys, or put keys in command arguments or documents. Use resources belonging to the same region and account.

Read the subcommand's `--help` first. Put global `--region`, `--json`, and `--timeout` options before the subcommand. Successful JSON goes to stdout and errors to stderr. Exit code 2 means a configuration/input error; 1 means a request error or terminal task failure.

## Choose a command

- Balance/uploads: `account balance`, `image upload`, and `media upload`. Upload with exactly one of `--file` or `--url`. URLs must use HTTPS with the default port or port 443, without embedded credentials, fragments, or whitespace. Vendor domains are not restricted.
- Usage: `account usage` queries consumption/refund entries for the current key. Supply start-time/end-time on the first page; timestamps use UTC+8 for `cn` and UTC for `global`, with an inclusive start and exclusive end. Platform validates the date ordering and time window. Repeat creation-type/credits-status as needed, request one page at a time, and pass only the unchanged cursor for subsequent pages.
- Video templates: `template list` queries video templates and supports template-id/mode/page/page-size. `template generate --id` reads metadata before submitting and supports video-only outputs. Standard templates require model/duration/quality and one image or ordered repeated img-id values. Workflows use repeated input JSON objects, each with input_key and exactly one of text/img_id/video_media_id/source_video_id/audio_media_id. Platform validates text defaults and dynamic input_limit rules. Query available templates first, do not invent node keys, and do not fall back across regions.
- Basic T2V/I2V supports webhook-id and negative-prompt. The server validates model combinations. Do not replace omitted options with explicit defaults.
- Basic generation: `video generate` (T2V), `video from-image` (I2V), `video f2v`, and `video fusion`. The I2V prompt is optional and accepts at most 5000 characters when supplied. Its aspect ratio follows the input image; no aspect-ratio option is provided.
- Sound effects: `video sound-effect` takes exactly one video source and optional sound-effect-content and original-sound switches. Do not supply a model or resolution.
- Multi-frame transitions: `video multi-transition` defaults to V5 and requires at least two ordered `--frame` JSON objects. Each segment duration belongs to its starting frame; omit duration or use 0 on the final frame. Platform validates maximum frame counts, segment durations, and total duration; the CLI does not rewrite them.
- Editing: `video extend`, `expand`, `upscale`, `restyle`, `mimic`, `swap`, and `modify`.
- Speaking characters: `video lipsync` and `video avatar`. Supply either `--audio-media-id` or both `--tts-speaker-id` and `--tts-content`. Avatar supports 360p/540p/720p/1080p and an optional prompt of up to 2048 characters. Avatar TTS requires 30-200 Unicode code points; Platform validates the actual text.
- Prerequisite queries: `voice list`, `video restyle-list`, and `video mask`.
- Custom voices: upload a speech sample of at most 30 seconds, then call `voice create --name ... --audio-media-id ...`. `voice list --type custom|system|all --scene avatar|lip_sync` uses the new voice list and preview fields. Omitted type defaults to all, with 20 entries per page; page-size supports only 10/20/50/100. Use the returned `custom_` voice ID for LipSync/Avatar TTS. `voice delete --speaker-id ...` deletes only the explicitly selected custom voice and does not retry automatically.
- Ecommerce uses only `agent ecommerce-native` (414562414124107) or `agent ecommerce-template` (414562414124108), not substitute agents. Require at least one nonempty image reference, prompt, a duration of 15/30/45/60 seconds, and language-code. Platform validates image counts and avatar eligibility. Template additionally requires video-style.
- Ecommerce `--image-ref` supports img_id/ref_name and preserves reference names; it is mutually exclusive with `--img-id`. Do not assume a numeric TTS ID identifies the same voice across regions. Check names and languages with `voice list` first.
- MV: `agent mv` uses `vibe_mv_v3_custom`. Submit directly after uploading audio; asynchronous audio validation depends on the target backend deployment. Character images, Custom style images, lyric timestamps, and preserve-outfit are supported.

## Resources and parameters

Provide exactly one video source: `--source-video-id` or `--video-media-id`. Mask keyframe-id is optional; do not inject a default frame. Mask selection returns a synchronous result, not a video_id. Swap uses the same source video and the keyframe_id and string mask_id from the same mask response. Preserve the order of repeated `--mask-id` and `--img-id` options for Modify. Mask IDs require an explicit keyframe-id.

Fusion accepts repeated `--img-id` values or repeated `--image-ref` JSON objects with img_id/type/ref_name. Use `--video-ref` for video references. V6 Omni and aspect-ratio=auto are supported. Supply positive seconds for image mode and 0 for Omni video mode; omitted duration is not injected. Platform validates model combinations, reference counts, and names.

When the user describes how specific assets should interact, use named references and rewrite those asset mentions in the prompt. For a person, jacket, and trail, pass the corresponding IDs with `ref_name` values `person`, `jacket`, and `trail`, and send `@person wears @jacket and walks along @trail`. Keep explicit names and creative details. Separate each mention from following punctuation with a space.

MV accepts at most one character image and one style image. Style images apply only to Custom, which requires at least one reference image. The server validates new styles; do not substitute an outdated enum for the user's selection. A lyrics file has the form `{"words":[{"start":0,"end":0.5,"word":"Hello"}]}`. start/end must be finite nonnegative numbers. Platform validates ordering, non-overlap, word counts, and alignment with the actual audio duration. Explicit `--no-caption`, `--no-lip-sync`, and `--no-preserve-outfit` preserve false.

## Submission and queries

Creation can consume production credits and requires user authorization. A response with `submission=accepted` and `response.Resp.video_id` indicates acceptance. By default, report only the ID; query proactively only when the user requests waiting or monitoring. Use `pixverse-api --region <selected-region> --json video get --id <video_id>` with the region used for creation, or the returned `query_command`. Do not recreate the task.

Workflow template creation returns `response.Resp.task_id`. Query it with `pixverse-api --region <selected-region> --json template get --id <task_id>`; do not treat task_id as video_id. Successful video links appear in output_urls, with output_url also provided for a single link. Template access does not expand scope to image/mixed outputs or previously excluded agents.

`task_status` normalizes both ordinary numeric statuses and agent running/succeeded/failed statuses. Successful results use `output_url`, while response preserves the original protocol. `output_url_verified=false` means the CLI did not probe the link; do not claim the output is accessible. A network timeout may occur after task creation, so do not directly retry writes. `Resp.credits` does not replace the final billing ledger.

JSON also includes `stage` and `submission_state`: local validation or template discovery failure is `not_submitted`, explicit Platform business refusal is `rejected`, a confirmed write is `accepted`, and uncertain outcomes such as write timeouts or successful responses without valid IDs are `unknown`. Read-only operations use `not_applicable`. Unknown does not mean unaccepted or uncharged; do not resend directly. Terminal failures return `ok=false` and exit code 1. Input errors include the field, constraint, and allowed values. Public upstream errors are retained in error.response with sensitive information redacted.

The CLI validates only its packaged public contract. Platform handles model availability, counts, permissions, moderation, billing, and dynamic template rules. Do not downgrade models or omit user requirements.
