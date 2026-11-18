---
name: pixverse-api
description: Generate and edit videos, upload assets, and query tasks and usage with PixVerse through a connected MCP service or the pixverse-api CLI. Offer showcase guidance to first-time users.
---

# PixVerse API

Map the user's intended result to an available PixVerse capability and execute it through MCP or the CLI. Preserve explicitly requested subjects, assets, models, duration, aspect ratio, resolution, and audio options. If the selected integration cannot express a requirement, explain the gap rather than submitting a reduced request.

## Choose an integration

1. Honor an explicit request for CLI or MCP. Otherwise, prefer a connected PixVerse MCP service that has already exposed the required tools. If no MCP service is available, use the installed `pixverse-api` CLI.
2. Read the [MCP guide](references/mcp.md) for MCP or the [CLI guide](references/cli.md) for CLI. Load only the integration details needed for the current request.
3. Use one integration for each operation. On authentication failure, insufficient permissions, timeout, or an uncertain write outcome, preserve the error, TraceId, and existing IDs. Do not switch integrations to resubmit. If submission is confirmed not to have occurred and the user agrees to change integrations, verify connection, account, and asset ownership again.
4. Use the discovered MCP tool names and input schemas, or the installed CLI's `--help`, as the parameter contract. Client service names can have arbitrary prefixes; do not infer a region, environment, or account from an alias.
5. Credentials come from client configuration or the runtime environment. Do not read authentication files, print keys, or ask users to send keys in chat. Use resources only with their owning connection and account. Reconfirm resource references after changing connections.

## Beginners and showcases

When users say they are new, do not know what is possible, or want introductory examples, offer a natural one-line showcase suggestion and continue their request. Do not make viewing examples a prerequisite. Respond in the user's language; for example:

> New to PixVerse? I can show you a few video examples. Pick an effect you like, and I can help you recreate it.

Usually offer this once per session. A short question does not establish the user's experience level; do not label the user a beginner. When the goal is clear or the user declines examples, proceed directly. Read the [showcase guide](references/showcase.md) when recommending or recreating a case. Select two or three relevant examples and present their direct CDN previews; load the selected case's original prompts and recorded settings from [showcase data](references/showcase.json).

## Capabilities and assets

- Basic generation: text-to-video T2V, image-to-video I2V, first/last-frame F2V, and multi-reference Fusion. I2V follows the input image's aspect ratio. Select Fusion image/video references and duration behavior according to the current contract.
- When a Fusion request refers to specific assets in ordinary language, bind those roles before submitting. For “Have him wear this jacket and walk along this trail,” give the three references unique `ref_name` values such as `person`, `jacket`, and `trail`. Write the prompt as `@person wears @jacket and walks along @trail`. Keep the user's actions, details, and any existing matching names. Each mention must match the name on its actual asset and end with a space or the end of the prompt. Put punctuation after a space. If the intended asset is unclear, ask which one the user means.
- Video editing: Extend, Expand, Upscale, Restyle, Mimic, Swap, and Modify. Use SoundEffect and MultiTransition for audio effects and transitions. SoundEffect produces a video with sound effects.
- Avatar takes a character image; LipSync takes a source video. Both accept either uploaded audio or a voice ID with TTS text, not a mixture of the two. Check the actual voice list for names, languages, and supported scenes. The same numeric ID may identify different voices on different connections.
- For Swap or Modify, pair the same source video with the actual `keyframe_id` and `mask_id` returned by mask selection. A requested frame index or mask image URL is not a returned ID.
- Custom voices follow "upload speech sample -> create voice -> use the returned `speaker_id`." Delete only a custom voice explicitly selected by the user; do not automatically clean up other voices.
- Use the dedicated ecommerce Native and Template capabilities; do not substitute real-estate or other agents. MV uses unified V3 Custom. Platform validates uploaded audio asynchronously; do not require an additional audio verification tool.
- Query template metadata first. Standard templates use traditional generation parameters. Workflows use the actual input names declared in metadata; do not invent `input_key` values or mix the two parameter formats.
- `img_id` references an image, `media_id` references uploaded video or audio, `video_id` identifies a generated video task, and workflows return `task_id`. Preserve types and ordering. Do not reuse historical IDs from a showcase directly.

The selected tool's contract defines enums, required fields, mutually exclusive inputs, and model combinations. Keep omitted options omitted and preserve explicit `false` and `0` values. Platform determines dynamic availability, permissions, moderation, and billing. Do not downgrade or substitute user-selected options.

## Submission, queries, and results

- Submit only within the user's authorized generation scope. Installation, connectivity checks, and viewing examples do not authorize paid generation. Track a supplied budget cumulatively; a creation quote does not replace the final billing ledger.
- Check `ok`, `stage`, and `submission_state`. `accepted` means accepted for processing, `not_submitted` means no submission occurred, `rejected` means the upstream explicitly refused it, and `unknown` means the outcome is unconfirmed. An unknown outcome does not mean no charge occurred; do not automatically resend.
- Report returned IDs after creation. Do not poll by default. If the user explicitly requests waiting or monitoring, query the same ID, respect upstream waiting guidance and the session's time limit, and avoid tight polling loops.
- Query ordinary generation and standard-template `video_id` values through video queries; query workflow `task_id` values through workflow queries. Never regenerate just to obtain a result.
- `completed` can coexist with `output_url_verified=false`: task completion does not prove the link was checked. For end-to-end acceptance, verify that the final output URL is accessible. Without an accessible final output, do not report a case as fully successful.
- Return output links, status, and necessary IDs; include public errors and TraceId on failure. Do not add connection aliases or deployment region/environment details by default. If asked, explain them accurately using known configuration.
