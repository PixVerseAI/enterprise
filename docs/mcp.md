# MCP Guide

[Home](../README.md) · [Installation](installation.md) · [CLI guide](cli.md)

## Connection and authentication

Run `python3 scripts/install_mcp.py` from a clone to configure remote MCP and install the original shared skill together. It defaults to `global`, independently of prompt language. An explicit China service request uses `--region cn`; follow the [installation guide](installation.md#install-mcp-and-skill-only) for service selection and DeepSeek profiles. This is **Streamable HTTP**, not a local stdio server or the legacy HTTP+SSE transport. No CLI installation is required.

The client sends `Authorization: Bearer <API key>` on requests. Provide the key through `PIXVERSE_OPENAPI_KEY` in the client process's environment or the client's supported secret store. This service uses API key authentication without OAuth sign-in.

For Pi, add the following to its MCP configuration, using the endpoint documented by your README:

```json
{
  "mcpServers": {
    "pixverse": {
      "type": "http",
      "url": "https://app-api.pixverse.ai/opanapi/mcp",
      "headers": {
        "Authorization": "Bearer ${PIXVERSE_OPENAPI_KEY}"
      }
    }
  }
}
```

Client configuration is not a universal MCP standard. In particular:

| Client | Configuration notes |
|---|---|
| Pi | The example uses `mcpServers`, `type: http`, and `${VARIABLE}` in headers. Use a literal endpoint URL. |
| WorkBuddy CLI | Use its supported `http` type and `${VARIABLE}` header syntax. Do not substitute an unrecognized `streamableHttp` spelling. |
| OpenCode | Remote entries use `type: remote`, `oauth: false`, and `{env:VARIABLE}` interpolation. Use the structure supported by the installed client version. |
| DeepSeek Harness | Its MCP client extension uses the explicit `streamable-http` transport. Configure headers through the extension's supported environment mechanism. |

Variable expansion happens in the client. The variable must exist in that process before startup; a variable in an interactive shell is not necessarily available to a desktop app. Reloading a configuration file does not populate a missing process environment. In Pi, `/reload` applies configuration changes; reconnect after service updates to refresh cached declarations.

The installer preserves unrelated settings and configures the native client format; the JSON above is a manual Pi example, not a universal configuration. Do not handwrite a replacement skill or leave a DeepSeek patch unregistered. See the [installation guide](installation.md) for directories and new-session checks. Never put real keys in committed JSON or tool business arguments.

## Verify the connection

1. Connect and discover the tool list. This service exposes 31 tools.
2. When authorized, ask the assistant to check the account balance using `account_balance`.
3. Inspect the actual tool result and business `ok` value. Tool discovery alone does not validate the account's API key.

Tools operate on the configured account. Business results and trace IDs do not contain deployment labels. A client may prefix tool names using its configured service alias; use discovered names rather than constructing aliases or inferring the target from them.

## Tools and input contracts

| Goal | Tool names before client prefixes |
|---|---|
| Balance and usage | `account_balance`, `account_usage` |
| Image, video, and audio uploads | `image_upload`, `media_upload` |
| Basic generation | `video_generate`, `video_from_image`, `video_f2v`, `video_fusion` |
| Editing | `video_extend`, `video_expand`, `video_upscale`, `video_restyle`, `video_mimic`, `video_swap`, `video_modify` |
| Avatars and lip sync | `video_avatar`, `video_lipsync` |
| Sound effects and transitions | `video_sound_effect`, `video_multi_transition` |
| Masks and styles | `video_mask`, `video_restyle_list` |
| Voice management | `voice_list`, `voice_create`, `voice_delete` |
| Templates | `template_list`, `template_generate`, `template_get` |
| Ecommerce and music videos | `agent_ecommerce_native`, `agent_ecommerce_template`, `agent_mv` |
| Video task queries | `video_get` |

Read descriptions and schemas from the connected service. Tool declarations list all input fields for client compatibility; complete contracts also specify exclusions and dependencies. Each tool links to an MCP resource at `pixverse://contracts/<tool-name>/input-schema`. Resource availability in a model's context depends on the client.

MCP enforces the published structural contract, including required fields, types, enums, ranges, and dependencies. Dynamic model/material combinations, template limits, account permissions, moderation, and billing are validated by Platform. There is no supplier-domain allowlist. Material and mask URLs must meet their published HTTPS schema.

The remote service cannot read a client-local file. Upload tools take a fetchable HTTPS `url`; a local file path is not a URL. Use an upload method explicitly authorized by the user, or request a usable link. The CLI is not an MCP prerequisite.

## Parameter planning

Use MCP field names from `tools/list`, which may differ from REST examples or CLI options.

| Operation | Important fields and behavior |
|---|---|
| V3 Custom MV | `audio_media_id`, one `img_id`, `mv_prompt`, `mv_style`, `caption`, `lip_sync`, `preserve_outfit`; audio validation is asynchronous. |
| Native / Template ad | `language_code`, such as `en-US`; Template additionally requires its declared `video_style`. |
| Voice creation / TTS | Create with `name` and `audio_media_id`; use the returned `speaker_id` as `tts_speaker_id` with `tts_content`. |
| Voice lookup | Omitted/null `speaker_type` means `all`; `custom` and `system` filter. The default page size is 20; allowed sizes are 10/20/50/100. |
| Template metadata | `template_list(template_ids=[...])`; a template definition ID is not a task ID. |
| Standard template result | The returned `video_id` is queried with `video_get`. |
| Workflow template result | The returned `task_id` is queried with `template_get`. |

I2V has an optional prompt up to 5000 characters. Avatar accepts 360p/540p/720p/1080p and an optional prompt up to 2048 characters. Platform validates Avatar TTS's 30–200 Unicode code-point requirement: minimum after trimming, maximum before trimming.

Fusion exposes `aspect_ratio=auto` for V6 Omni. Empty reference arrays are omitted. An omitted Fusion duration or Mask keyframe is forwarded without injecting a value; explicit `0` and `false` are preserved. Use positive duration for image mode and zero for Omni video mode, subject to Platform's combination checks. Reuse the actual source video, keyframe, and mask returned by Mask selection.

Preserve user-requested characters, styles, references, and audio switches. If an option cannot be represented, explain the limitation before submitting a reduced request. Do not change arguments merely to bypass a client's repeated-call warning.

## Results and errors

All 31 tools declare an `outputSchema`. Results contain matching JSON text and `structuredContent`. Some clients retain the MCP envelope; others unwrap it. For clients exposing either form, use:

```javascript
const data = result.structuredContent ?? result;
```

If the client only provides text content blocks, parse the actual JSON text. Check MCP `isError` when available and the business object's `ok`, `stage`, and `submission_state`. Original HTTP/business details, including `ErrCode`, `ErrMsg`, `Resp`, and `Error`, are retained in `response` or `error.response` with credentials redacted. Protocol errors identify the field, failed constraint, and declared allowed values.

| `submission_state` | Meaning |
|---|---|
| `not_submitted` | Validation or discovery failed before the business write. |
| `rejected` | Platform explicitly rejected the write. |
| `accepted` | A write was confirmed; generation is not necessarily complete. |
| `unknown` | A timeout or missing/invalid response ID leaves the write outcome uncertain. |
| `not_applicable` | Read-only operation. |

An `unknown` result does not mean no task was created or no credits were charged. Do not automatically resubmit it; retain its trace ID for investigation. Returned query URLs have `output_url_verified=false` because the server does not probe them.

## Long-running tasks

Keep the same task ID after acceptance. Query it once unless the user asks for continued monitoring. For authorized monitoring, follow upstream retry guidance, use the client's waiting support, and set a bounded total waiting period. Repeated status reads are not repeated generation.

The server does not automatically retry writes or poll task completion. A successful tool invocation or accepted submission is not a completed video. Check terminal task state and the final media link before reporting full success. A client repeated-call warning alone does not prove duplicate generation. Report connection failures or missing tools rather than silently switching to terminal commands or handwritten HTTP.
