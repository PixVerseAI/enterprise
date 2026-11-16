# PixVerse Enterprise

English | [简体中文](README.zh-CN.md)

Tools for the PixVerse Platform OpenAPI. This repository provides the production CLI, a skill for AI assistants, and connection instructions for the hosted MCP service. Available models, parameters, and features depend on the API and account permissions.

| Directory | Purpose |
|---|---|
| `cli/` | Production OpenAPI command-line client. |
| `skills/` | Instructions for AI assistants using the CLI. |

## CLI installation and configuration

Python 3.10 or later is required. From the repository root:

```bash
pipx install .
pixverse --help
```

Set `PIXVERSE_REGION=ov` and provide your production API key through `PIXVERSE_API_KEY` using a secure environment or secret manager. Do not put real keys in source control, command arguments, or chat. The CLI does not load `.env` files or local skill credentials.

Production Platform API: `https://app-api.pixverse.ai`.

The CLI uses the fixed production API URL. It does not accept arbitrary API base URLs, follow redirects, or use implicit proxies. Use keys, asset IDs, and task IDs belonging to the same API endpoint and account.

```bash
pixverse --json account balance
pixverse image upload --file /absolute/path/image.png
pixverse media upload --url https://example.com/audio.wav
pixverse video generate --prompt "A cat walking through a meadow" --no-audio
pixverse video from-image --img-id 123456 --prompt "The subject walks forward"
pixverse --json video get --id 123456
```

IDs and URLs above are examples. Replace them with resources belonging to the same API endpoint and account.

## CLI capabilities

| Capability | Commands |
|---|---|
| Account and assets | `account balance`, `account usage`, `image upload`, `media upload` |
| Video creation | `video generate`, `video from-image`, `video f2v`, `video fusion` |
| Editing and effects | `video extend`, `expand`, `upscale`, `restyle`, `sound-effect`, `multi-transition`, `mimic`, `mask`, `swap`, `modify` |
| Speaking characters | `video lipsync`, `video avatar`, `voice list`, `voice create`, `voice delete` |
| Templates and tasks | `template list`, `template generate`, `template get`, `video get`, `video restyle-list` |
| Agents | `agent ecommerce-native`, `agent ecommerce-template`, `agent mv` |

Use `pixverse <command> --help` for detailed options. Source-video operations require exactly one of `--source-video-id` or `--video-media-id`. LipSync and Avatar accept either an audio media ID or both TTS fields. Mask selection is a separate step; Swap requires a mask and keyframe from the same source video.

The two ecommerce commands use their respective fixed agent IDs. MV uses `vibe_mv_v3_custom`; audio validation is asynchronous where supported by the target backend. Template generation first checks template metadata; standard templates return a `video_id`, whereas workflow templates return a `task_id`. Custom voice deletion only accepts a `custom_` speaker ID.

`account usage` queries consumption and refunds for the current key. The first page requires `--start-time` and `--end-time` in `YYYY-MM-DD HH:MM:SS` format, covers at most 30 days, and is interpreted in UTC. Later pages use the returned cursor without other filters. The default page size is 50 and the maximum is 100.

```bash
pixverse --json account usage --start-time '2026-11-01 00:00:00' --end-time '2026-11-02 00:00:00' \
  --creation-type text_to_video --credits-status consume --limit 20
pixverse --json template list --mode standard --page 1 --page-size 20
pixverse --json template generate --id 123 --img-id 11 --model v5.6 --duration 5 --quality 720p
pixverse --json template get --id 234567
```

`template list` returns video template metadata. Standard template generation requires explicit model, duration and quality; supply images in order as required by the template. Workflow templates use named `--input` JSON objects from their input metadata and only video outputs are supported. API-side availability and permissions remain authoritative.

```bash
pixverse video f2v --first-frame-img 11 --last-frame-img 12 --prompt "Day turns to night"
pixverse video fusion --img-id 11 --img-id 12 --prompt "The subjects interact"
pixverse video extend --source-video-id 21 --prompt "Continue forward" --duration 5
pixverse video expand --video-media-id 22 --aspect-ratio 9:16 --quality 720p
pixverse video sound-effect --video-media-id 22 --sound-effect-content 'gentle rain' --no-original-sound
pixverse video multi-transition --frame '{"img_id":11,"duration":5}' --frame '{"img_id":12}'
pixverse video lipsync --video-media-id 22 --audio-media-id 41
pixverse video avatar --img-id 11 --tts-speaker-id Auto --tts-content "Welcome"
pixverse video mask --video-media-id 22 --keyframe-id 0
pixverse video swap --video-media-id 22 --keyframe-id 0 --mask-id 0 --img-id 12
```

I2V accepts an optional prompt of up to 5000 characters; its aspect ratio follows the input image. Fusion supports image references and V6 Omni video references, including `--aspect-ratio auto`. Omitted Fusion duration is not sent; explicit values, including zero, are preserved. Use positive seconds for image mode and zero for Omni video mode; Platform validates the actual combination. MultiTransition takes at least two ordered frames. Each duration applies to the starting frame of a segment; omit it or set zero on the final frame. Platform validates model-specific counts and duration limits. Modify supports mask IDs or mask URLs, not both; mask IDs require a keyframe ID. Mask selection accepts an optional keyframe ID without injecting a default, and does not automatically run Swap or Modify. Avatar accepts 360p/540p/720p/1080p and an optional prompt of up to 2048 characters; Platform validates Avatar TTS text requirements.

```bash
pixverse agent ecommerce-native --img-id 11 --prompt "Show the product" --duration 15 --language-code en-US
pixverse agent ecommerce-template --img-id 11 --prompt "Show the product" --duration 15 \
  --language-code en-US --video-style polished_commercials
pixverse agent mv --audio-media-id 41 --img-id 11 --mv-style Custom --preserve-outfit
pixverse voice create --name 'Brand voice' --audio-media-id 41
pixverse voice list --type custom --scene avatar --page-size 20
```

Ecommerce requires at least one image reference and a duration of 15, 30, 45 or 60 seconds. Platform validates image counts and avatar availability. The template variant also requires a supported video style. MV supports a character image and a Custom-only style image, with at least one image required for Custom. Optional lyric timestamps can be supplied from a local JSON file using `--lyric-timestamp-file`; start/end must be nonnegative finite numbers. Platform validates ordering, overlap, text and audio matching. Custom voice creation uses an uploaded audio sample of at most 30 seconds; availability and limits are validated by Platform. `voice list` defaults to the combined system/custom endpoint, `--type all`, and 20 entries per page; supported page sizes are 10/20/50/100.

Submission may consume credits and only indicates that a task was accepted. Use `video get` or `template get` to check its status. The CLI does not automatically retry writes, poll tasks, or download results. A returned result URL is not independently verified unless explicitly stated. If a write times out, check its status before submitting again.

JSON responses include region, environment, trace ID, HTTP status and the platform response with sensitive fields redacted. They also include `stage` and `submission_state`: validation/discovery failures before a write are `not_submitted`, explicit Platform business rejection is `rejected`, confirmed writes are `accepted`, and ambiguous write outcomes such as timeouts or missing/invalid response IDs are `unknown`. Read-only operations use `not_applicable`, including usage queries sent by POST. Never automatically resubmit an unknown write. Task queries also return a normalized `task_status`; failed or rejected terminal tasks return `ok=false` and exit code 1. Unknown states are preserved without inferring completion. Exit code 0 indicates a successful request, including a task still in progress; 2 indicates invalid configuration or input, and 130 indicates interruption. Errors are written to stderr; published input errors identify fields and constraints, and upstream public error messages are preserved.

The CLI independently packages its input contracts and validates required fields, types, enums, ranges, and declared dependencies. Dynamic model/material combinations, template `input_limit`, time windows, permissions, moderation, and billing are validated by Platform. URL uploads and mask URLs require HTTPS on the default port or 443, with no embedded credentials, fragments, or whitespace; there is no supplier-domain allowlist. Local file uploads remain supported. CLI packaging does not depend on the MCP server; offline tests validate the CLI's packaged input contract.

For CLI development:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" PIXVERSE_FORCE_INSTALLED=1 .venv/bin/python -m pytest -q tests
.venv/bin/ruff check cli tests
.venv/bin/python -m build
```

## Remote MCP access

Connect to `https://app-api.pixverse.ai/opanapi/mcp` using an MCP client that supports Streamable HTTP and custom headers. No local server or CLI installation is required.

Provide your API key to the client process through the `PIXVERSE_OPENAPI_KEY` environment variable. For Pi and other clients supporting `${VARIABLE}` expansion, use:

```json
{
  "mcpServers": {
    "pixverse-enterprise": {
      "url": "https://app-api.pixverse.ai/opanapi/mcp",
      "headers": {"Authorization": "Bearer ${PIXVERSE_OPENAPI_KEY}"}
    }
  }
}
```

Environment-variable expansion is performed by the MCP client. If your client uses a different syntax or a secure credential store, configure the same Bearer authentication header through its supported mechanism. Keep real keys out of JSON files and source control. Start the client after setting the variable; in an existing Pi session, use `/reload` for configuration-file changes.

Tools operate on the currently connected PixVerse account. Configure the service URL and your account's API key in the client. Results contain business data and trace IDs for troubleshooting, without deployment labels. This version uses API key authentication without OAuth sign-in. To verify authentication, call `account_balance` and inspect its result; tool discovery alone does not validate the key.

Material and mask URLs must follow the tool URL schema; no supplier-domain allowlist is required. MCP validates the published parameter contract and forwards dynamic model, template, material, and account checks to Platform. It does not read client-local files. Generation may consume credits; a successful submission means the task was accepted. Use the corresponding query tool to check its status. Writes are not automatically retried or polled.

Protocol errors identify the field and failed constraint, including declared allowed values. Platform HTTP status, ErrCode, ErrMsg, Resp and Error details are preserved with credentials redacted. The existing template routing lookup and video-only scope remain supported; no new mode argument is required.

Tool declarations list all input fields for client compatibility. The server still enforces the complete input contract, including mutual exclusions and dependencies. Each tool links to its machine-readable contract at `pixverse://contracts/<tool-name>/input-schema`, available through MCP resources. Reconnect or reload your client after a server update to refresh cached declarations.

Use the MCP field names shown in `tools/list`; REST examples may use mapped names. In particular:

| Task | MCP fields or query tool |
|---|---|
| V3 custom MV | `audio_media_id`, single `img_id`, `mv_prompt`, `mv_style`, `caption`, `lip_sync`, `preserve_outfit` |
| Native / Template ad | `language_code` such as `en-US`; Template also requires the declared `video_style` |
| Voice creation / TTS | Create with `name` and `audio_media_id`; use the returned `speaker_id` as `tts_speaker_id` in Avatar or LipSync |
| Voice lookup | Omitted or null `speaker_type` means `all`; use `custom` or `system` to filter. The default page size is 20; allowed sizes are 10/20/50/100. All calls use the current voice-list endpoint |
| Template metadata | `template_list(template_ids=[...])`; a `template_id` is not a run ID |
| Standard / Workflow result | Standard creation returns `video_id` → `video_get`; Workflow returns `task_id` → `template_get` |

Keep user-requested characters, styles, references and audio switches in the submitted parameters. If a requested option cannot be expressed, explain before submitting a reduced request. Once accepted, keep the same task ID. Query once unless the user asks for continued monitoring; for long monitoring use the client's waiting support and upstream retry guidance. Repeated status reads are different from repeated generation. A client's repeated-call warning alone does not prove duplicate generation, and changing arguments to bypass that warning is not appropriate.

Avatar accepts `360p`, `540p`, `720p` and `1080p`; its optional prompt is limited to 2048 characters. Avatar TTS requires 30–200 Unicode code points (minimum after trimming; maximum before trimming), validated by Platform. Fusion exposes `aspect_ratio=auto` for the V6 Omni branch; model/material combinations remain subject to Platform validation. Empty Fusion reference arrays are omitted. An omitted Fusion duration or Mask keyframe is forwarded without injecting a value; explicit `0` and `false` values are preserved. Reuse the actual keyframe and mask returned by Mask selection.

All 31 tools declare an `outputSchema`. Tool results contain matching JSON text and `structuredContent`. Clients that retain the MCP result envelope, including Pi 1.5.2 codemode, expose the payload under `result.structuredContent`; clients that unwrap it expose the payload directly. Use `const data = result.structuredContent ?? result` rather than parsing a JSON string. Original business fields remain in `response` or `error.response`, with credentials redacted. Check `ok`, `stage` and `submission_state`: local validation or discovery failures before a write are `not_submitted`, explicit Platform rejection is `rejected`, a confirmed write is `accepted`, and ambiguous outcomes such as a write timeout or a success response missing its ID are `unknown`. Read-only calls use `not_applicable`. `accepted` does not mean generation completed, and `unknown` does not mean no credits were charged. Do not automatically resubmit; retain the trace ID for investigation. Query URLs carry `output_url_verified=false` because this service does not probe them.

## Platform documentation

- [PixVerse Platform API](https://docs.platform.pixverse.ai/)

Request parameters, model availability, prices, and entitlements are determined by the API documentation and actual responses.
