# CLI Guide

[Home](../README.md) · [Installation](installation.md) · [MCP guide](mcp.md)

## Configuration

The command is `pixverse-api`. Install the CLI and shared skill with `python3 scripts/install.py`; see the [installation guide](installation.md) for prerequisites and client directories.

Provide the account's production API key through `PIXVERSE_OPENAPI_KEY` in your environment or secret manager. The CLI does not load `.env` files or skill credentials. Keep keys out of command arguments, chat, and source control.

The root option `--region global|cn` selects the production API; `global` is the default. There is no region environment variable. Use the endpoint documented by your chosen README, and keep the key, asset IDs, and task IDs associated with that endpoint and account. Arbitrary API base URLs, redirects, and implicit proxies are not supported.

Global options precede subcommands:

```bash
pixverse-api --json --timeout 60 account balance
pixverse-api --region cn --json account balance
pixverse-api video from-image --help
```

Examples below use placeholder IDs and paths. Replace them with your own resources. Generation commands may consume credits; they are not installation checks.

## Command reference

| Capability | Commands |
|---|---|
| Account and assets | `account balance`, `account usage`, `image upload`, `media upload` |
| Basic generation | `video generate`, `video from-image`, `video f2v`, `video fusion` |
| Editing and effects | `video extend`, `expand`, `upscale`, `restyle`, `sound-effect`, `multi-transition`, `mimic`, `mask`, `swap`, `modify` |
| Speaking characters | `video lipsync`, `video avatar` |
| Voices | `voice list`, `voice create`, `voice delete` |
| Templates and tasks | `template list`, `template generate`, `template get`, `video get`, `video restyle-list` |
| Agents | `agent ecommerce-native`, `agent ecommerce-template`, `agent mv` |

Use `pixverse-api <command> --help` for all options, types, and allowed values.

## Assets and basic generation

```bash
pixverse-api image upload --file /absolute/path/image.png
pixverse-api media upload --url https://example.com/audio.wav
pixverse-api video generate --prompt "A cat walking through a meadow" --no-audio
pixverse-api video from-image --img-id 11 --prompt "The subject walks forward"
pixverse-api video f2v --first-frame-img 11 --last-frame-img 12 --prompt "Day turns to night"
pixverse-api video fusion \
  --image-ref '{"img_id":11,"ref_name":"person"}' \
  --image-ref '{"img_id":12,"ref_name":"jacket"}' \
  --image-ref '{"img_id":13,"ref_name":"trail"}' \
  --prompt '@person wears @jacket and walks along @trail'
pixverse-api --json video get --id 21
```

I2V accepts an optional prompt of up to 5000 characters; the aspect ratio follows the image. Fusion supports repeated `--img-id` or `--image-ref` JSON objects with `img_id` and optional `type` and `ref_name`. V6 Omni also supports `--video-ref` and `--aspect-ratio auto`. Each video reference uses one video source and an optional `ref_name`.

For requests like “have him wear this jacket,” use the uploaded IDs for the corresponding assets and refer to each by its exact name in the prompt. A space or the end of the prompt terminates a mention. For example, write `At @trail , @person wears @jacket`. A generic prompt that doesn't assign roles can still use unnamed references.

An omitted Fusion duration is not sent; explicit values, including zero, are preserved. Use positive seconds for image mode and zero for Omni video mode. Platform validates the actual model/material combination, reference counts, and names.

Local uploads remain supported. Uploaded media and mask URLs require HTTPS on the default port or 443, without embedded credentials, fragments, or whitespace. There is no supplier-domain allowlist.

## Usage and templates

`account usage` queries consumption and refunds for the current key. The first page requires `--start-time` and `--end-time` in `YYYY-MM-DD HH:MM:SS` format. Times use UTC for `global` and UTC+8 for `cn`; the end is exclusive. The API supports a window of up to 30 days and validates time-window rules. The default page size is 50; the maximum is 100. For subsequent pages, pass the returned cursor without other filters.

```bash
pixverse-api --json account usage --start-time '2026-11-01 00:00:00' --end-time '2026-11-02 00:00:00' \
  --creation-type text_to_video --credits-status consume --limit 20
pixverse-api --json account usage --cursor 'RETURNED_CURSOR'
pixverse-api --json template list --mode standard --page 1 --page-size 20
pixverse-api --json template generate --id 123 --img-id 11 --model v5.6 --duration 5 --quality 720p
pixverse-api --json template get --id 234567
```

Template generation discovers metadata before submitting. Standard templates require explicit model, duration, and quality, with images ordered as required by the template. Workflow templates accept named `--input` JSON objects from the template's input metadata. Only video outputs are supported. Availability, permissions, and dynamic `input_limit` rules are validated by Platform.

A standard template returns a `video_id`, queried with `video get`; a workflow template returns a `task_id`, queried with `template get`. A template definition ID is not a generated task ID.

## Video editing

Source-video operations require exactly one of `--source-video-id` or `--video-media-id`.

```bash
pixverse-api video extend --source-video-id 21 --prompt "Continue forward" --duration 5
pixverse-api video expand --video-media-id 22 --aspect-ratio 9:16 --quality 720p
pixverse-api video sound-effect --video-media-id 22 --sound-effect-content 'gentle rain' --no-original-sound
pixverse-api video multi-transition --frame '{"img_id":11,"duration":5}' --frame '{"img_id":12}'
pixverse-api video mask --video-media-id 22 --keyframe-id 0
```

SoundEffect generates audio for a video. Omit the content to request automatic sound effects; this command does not take a model or quality option. MultiTransition accepts at least two ordered `--frame` objects with `img_id` and optional prompt/duration. Each duration belongs to the starting frame of a segment; omit duration or set zero on the last frame. Platform validates model-specific frame counts and segment/total duration limits.

Mask selection is a separate operation. It accepts an optional keyframe ID without injecting a default and does not run Swap or Modify. There is no `mask_prompt` option. Reuse the actual keyframe and mask IDs from its response for the same source video; IDs may be strings, including `"0"`.

```bash
pixverse-api video swap --video-media-id 22 --keyframe-id RETURNED_KEYFRAME --mask-id RETURNED_MASK --img-id 12
pixverse-api video modify --video-media-id 22 --prompt "Replace the subject using the reference" \
  --img-id 12 --keyframe-id RETURNED_KEYFRAME --mask-id RETURNED_MASK
pixverse-api video restyle-list
```

Modify preserves the order of repeated images and masks. Mask IDs require `--keyframe-id`; mask URLs are supported by Modify only and cannot be mixed with mask IDs. Swap only accepts mask IDs. Mimic, Swap, and Modify do not support 1080p output. Query current style IDs with `video restyle-list`.

## Avatar, LipSync, and custom voices

Avatar uses an image; LipSync uses a source video. Provide either `--audio-media-id` or both `--tts-speaker-id` and `--tts-content`, without mixing the two input modes.

```bash
pixverse-api voice list
pixverse-api video lipsync --video-media-id 22 --audio-media-id 41
pixverse-api video avatar --img-id 11 --audio-media-id 41
pixverse-api media upload --file /absolute/path/voice-sample.wav
pixverse-api voice create --name 'Brand voice' --audio-media-id 41
pixverse-api --json voice list --type custom --scene avatar --page-size 20
```

Avatar supports 360p/540p/720p/1080p and an optional prompt of up to 2048 characters. Platform validates Avatar TTS text, including its 30–200 Unicode code-point requirement. Select a suitable `speaker_id` returned by the voice list or creation response for TTS; do not invent one.

`voice list` defaults to `--type all` and 20 entries per page. It supports `system|custom|all`, `--scene avatar|lip_sync`, and page sizes 10/20/50/100; all modes use the current voice-list endpoint. Availability and preview URLs are supplied by Platform.

Custom voice creation uses an uploaded sample of at most 30 seconds and synchronously returns `speaker_id`; it is not a video task. IDs belong to the original account and endpoint. Platform validates membership, sample limits, and creation quotas.

Delete only an intended custom voice with `voice delete --speaker-id custom_RETURNED_ID`. Deletion accepts a `custom_` ID and supports success responses with null or empty `Resp`; it is not automatically retried.

## Ecommerce and music videos

| Command | Fixed agent ID | Additional requirement |
|---|---|---|
| `agent ecommerce-native` | `414562414124107` | Images, prompt, duration, and language code |
| `agent ecommerce-template` | `414562414124108` | The same fields plus `video-style` |

These commands do not expose an arbitrary `agent_id`. Durations are 15/30/45/60 seconds; quality is 720p/1080p; the default aspect ratio is 9:16. Template styles are `polished_commercials`, `personal_review`, and `no_personal_review`; Native does not accept this option.

```bash
pixverse-api agent ecommerce-native --img-id 11 --prompt "Show the product" --duration 15 --language-code en-US
pixverse-api agent ecommerce-template --img-id 11 --prompt "Show the product" --duration 15 \
  --language-code en-US --video-style polished_commercials
pixverse-api agent mv --audio-media-id 41 --img-id 11 --mv-style Custom --preserve-outfit
```

Ecommerce accepts either repeated `--img-id` or repeated `--image-ref '{"img_id":11,"ref_name":"product"}'`, without mixing them. References contain only `img_id` and optional `ref_name`. Use `--avatar Auto` or a model image ID string; Platform ignores avatar for `no_personal_review`. Lip sync, background music, and captions have explicit positive/negative flags. Omission uses the server default. Platform validates image counts, avatar availability, and voice IDs.

MV exposes only `vibe_mv_v3_custom`, without an arbitrary type override. Upload audio and submit MV directly; audio validation is asynchronous in the supported backend. There is no separate `media verify-audio` step. Accepted submission does not prove moderation or generation succeeded.

MV accepts at most one character image and one style image. Style images are Custom-only, and Custom requires at least one image reference. Optional fields include `--mv-prompt`, `--music-style`, `--lyric-text`, `--caption`, `--lip-sync`, and `--preserve-outfit`, with explicit false values preserved. Platform validates current styles, audio duration, permissions, and moderation.

Use `--lyric-timestamp-file /absolute/path/lyrics.json` for `{"words":[{"start":0,"end":0.5,"word":"Hello"}]}`. Times are nonnegative finite numbers in seconds. Platform validates ordering, overlap, text, and audio matching. When supplied with plain lyric text, timestamps take precedence according to the API contract.

## Results and automation

JSON includes `ok`, `region`, `environment`, `trace_id`, `http_status`, and the original Platform structure in `response`, with sensitive fields redacted. Requests have a new UUID v4 `Ai-trace-id`. Both HTTP status and business `ErrCode` are checked; public `Error` details are retained.

| `submission_state` | Meaning |
|---|---|
| `not_submitted` | Validation or discovery failed before the business write. |
| `rejected` | Platform explicitly rejected the write. |
| `accepted` | The write was confirmed; generation may still be running. |
| `unknown` | A timeout or invalid/missing response ID leaves the write outcome uncertain. |
| `not_applicable` | Read-only operation, including POST-based usage queries. |

Check `stage` alongside `submission_state`. Do not automatically resubmit an unknown write; it may already have been accepted or charged. The CLI does not automatically retry writes, poll tasks, or download media.

Task queries add `task_status`: `completed`, `generating`, `moderation_failed`, `failed`, or `unknown`. Numeric video states and workflow string states are normalized; unknown states remain unknown. `output_url` comes from `Resp.url` or `Resp.output.video`, and `output_url_verified=false` means the CLI has not probed it. Use the usage ledger to reconcile consumption/refunds; `Resp.credits` alone does not establish final cost.

| Exit code | Meaning |
|---|---|
| 0 | Successful request, including a task still running. |
| 1 | Request failure or a failed/rejected terminal task. |
| 2 | Invalid input or configuration. |
| 130 | Interrupted execution. |

Errors go to stderr; failed terminal task queries still expose their structured result on stdout. Published input errors identify fields and constraints; upstream public errors are preserved.

The CLI packages and validates the formal input contract: required fields, types, enums, ranges, exclusions, and dependencies. Dynamic model/material combinations, template limits, time windows, permissions, moderation, and billing remain Platform's responsibility. The CLI package is independent of the MCP service.
