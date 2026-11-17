# MCP Integration

Use the remote PixVerse MCP service configured in the current client over Streamable HTTP. MCP calls Platform APIs directly and does not require installing or running the CLI.

## Tool discovery

Discover tools from the current client's connected services. Read the description and complete input schema for each required tool, and load contract resources as needed. Clients may add tool prefixes; use the names actually discovered rather than constructing a fixed service alias or inferring the account or target from an alias.

| Goal | MCP tool names without client prefixes |
|---|---|
| Balance and usage | `account_balance`, `account_usage` |
| Image, video, and audio uploads | `image_upload`, `media_upload` |
| Basic generation | `video_generate`, `video_from_image`, `video_f2v`, `video_fusion` |
| Editing | `video_extend`, `video_expand`, `video_upscale`, `video_restyle`, `video_mimic`, `video_swap`, `video_modify` |
| Avatars and lip sync | `video_avatar`, `video_lipsync` |
| Sound effects and multi-frame transitions | `video_sound_effect`, `video_multi_transition` |
| Mask selection and style lists | `video_mask`, `video_restyle_list` |
| Voice management | `voice_list`, `voice_create`, `voice_delete` |
| Video effect templates | `template_list`, `template_generate`, `template_get` |
| Ecommerce and music videos | `agent_ecommerce_native`, `agent_ecommerce_template`, `agent_mv` |
| Ordinary video task queries | `video_get` |

These names help select capabilities; the connected service's actual tools and contracts remain authoritative. If the requested MCP service is disconnected or a tool is missing, report the specific gap. Do not claim to call a nonexistent tool or automatically substitute terminal commands or handwritten HTTP requests.

## Inputs

- The client supplies business authentication through request headers; client examples use `PIXVERSE_OPENAPI_KEY`. Do not put keys in tool business arguments, read authentication files, or ask the model to transfer authentication headers.
- The current upload tools accept a fetchable HTTPS `url`. A local file path is not a URL. Obtain a usable link through an upload method explicitly authorized by the user, or ask for a link. Do not make the CLI a prerequisite for MCP.
- Use the schema's original field names rather than CLI `--option` names. For example, Avatar and LipSync use `tts_speaker_id` and `tts_content`; MV characters use `img_id` and creative instructions use `mv_prompt`.
- Query metadata with `template_list(template_ids=[...])`. Query a standard template's returned `video_id` with `video_get`; query a workflow's returned `task_id` with `template_get`. These ID types are not interchangeable.
- Use `speaker_type` and `scene` with `voice_list` to find suitable voices. For custom voices, use the `speaker_id` returned by voice creation in subsequent TTS requests.

## Results

Clients may retain the MCP envelope or return the business object directly. When the envelope is retained, prefer `result.structuredContent`; when already unwrapped, read the object directly. If only text content blocks are available, parse their actual JSON content. A completed tool invocation does not mean generation succeeded.

Check both MCP `isError` and the business object's `ok`, `stage`, and `submission_state`. Preserve public errors from `response` or `error.response`. Follow the main skill's rules for acceptance, failure, uncertainty, task queries, and media accessibility. Do not change parameters or switch to CLI to resubmit a failed business operation.
