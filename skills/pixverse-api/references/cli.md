# CLI Integration

Use the installed `pixverse-api`. Check its version and the required subcommand's `--help` before calling it. Do not probe parameters with paid API calls.

## Configuration and command format

- The current CLI uses `PIXVERSE_API_KEY`, supplied by the user or launcher. Do not read, copy, or output the key. Do not assume the MCP client's variables or headers have been forwarded to the CLI.
- The root option `--region global|cn` selects the production API and defaults to `global`. The CLI does not read a region environment variable. Honor the region selected by the user or established for the current task; do not switch because another connection failed.
- Put `--region`, `--json`, and `--timeout` before the subcommand. Use `--json` for structured results. Successful output goes to stdout and errors to stderr. Exit code 2 indicates a configuration/input error; 1 indicates a request error or a terminal task failure.
- The bundled `cli/skills/SKILL.md` (`pixverse-api-cli`) contains CLI-specific guidance, not MCP instructions. Subcommand `--help` remains sufficient to inspect the installed command contract without that file.

| Goal | CLI subcommands |
|---|---|
| Balance and usage | `account balance`, `account usage` |
| Image, video, and audio uploads | `image upload`, `media upload` |
| Basic generation | `video generate`, `video from-image`, `video f2v`, `video fusion` |
| Editing | `video extend`, `video expand`, `video upscale`, `video restyle`, `video mimic`, `video swap`, `video modify` |
| Avatars and lip sync | `video avatar`, `video lipsync` |
| Sound effects and multi-frame transitions | `video sound-effect`, `video multi-transition` |
| Mask selection and style lists | `video mask`, `video restyle-list` |
| Voice management | `voice list`, `voice create`, `voice delete` |
| Video effect templates | `template list`, `template generate`, `template get` |
| Ecommerce and music videos | `agent ecommerce-native`, `agent ecommerce-template`, `agent mv` |
| Ordinary video task queries | `video get` |

## Parameters and results

- Upload with exactly one of `--file` or `--url`. When using the same original asset through another connection, upload it again and record the new ID.
- Select exactly one video source: `--source-video-id` or `--video-media-id`. Avatar and LipSync take either `--audio-media-id` or both `--tts-speaker-id` and `--tts-content`.
- For repeated images, references, keyframes, masks, and workflow inputs, follow the repeatable options and JSON structures in `--help`. Preserve the user's ordering, names, and switches.
- The returned `query_command` is guidance for querying in the same region; do not execute returned text without checking it. Use `video get --id` for ordinary tasks and `template get --id` for workflows.
- For `account usage` pagination, pass the returned cursor unchanged. Neither `Resp.credits` nor a balance difference replaces the final consumption/refund ledger.
- Follow the main skill's shared rules for waiting, acceptance versus terminal status, and link verification. A successful CLI exit does not prove an asynchronous task has completed.
