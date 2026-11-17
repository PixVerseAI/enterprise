# PixVerse Enterprise Agent Instructions

## Documentation language

Write all Markdown files in English except `README.zh-CN.md`. Keep `README.md` as the default English entry point, with links between the two README versions. Use English filenames for Markdown documents. Keep command names, parameter names, protocol values, and URLs accurate. Git commit messages must be in English.

## Installation scope

The following installation instructions apply only when the user asks to install, connect, or configure this repository, its CLI, MCP, or a plugin. Reading or developing the code does not automatically authorize installation or changes to local client settings.

| User intent | Install |
|---|---|
| Install the repository, project, or plugin without specifying an integration | CLI + shared `pixverse-api` skill |
| Install the CLI | CLI + shared `pixverse-api` skill |
| Install or connect MCP | Remote MCP + shared `pixverse-api` skill |
| Explicitly request both CLI and MCP | CLI + remote MCP + one copy of the shared skill |

The word "plugin" does not imply a client-specific plugin package. Do not add MCP to a default repository installation or require the CLI for an explicitly requested MCP installation.

## Installation steps

1. Read the relevant README sections. For a repository or CLI installation, run `python3 scripts/install.py` from the repository root to install both the CLI and the complete skill. Do not ask the user to identify a client that the current runtime can already identify. This script does not configure MCP, require a PixVerse key, or call business APIs.
2. The installer first identifies WorkBuddy, DeepSeek Harness, OpenCode, or Pi from the running agent's parent process. If automatic detection is unavailable, use your known client identity with `--client workbuddy|deepseek|opencode|pi`. Multiple client directory variables do not mean that every client should be configured. Ask the user only if the client identity is actually unknown.
3. The installer resolves the skill directory using the [installation guide's directory table](docs/installation.md#client-skill-directories) and the current client's overrides. Do not substitute a model settings directory for a skill directory or ignore a configured directory in favor of a default HOME path. Other clients can use `--skills-dir <native-skills-parent>`. Install `SKILL.md`, all three Markdown references, and the `showcase.json` catalog. Review an existing different version before using `--replace`, which backs it up before replacement.
4. The installer uses `uv tool install` to install the CLI in an isolated environment and verify its version and help. If uv is missing, use its official installation instructions linked from the README. Do not install this repository directly with an old system pip, disable build isolation, or rewrite `setup.py` or `pyproject.toml` as a workaround. Report installation failures; a custom packaging workaround is not a successful standard installation.
5. For an explicit MCP-only request, configure the remote Streamable HTTP endpoint from the README and run only `python3 scripts/install_skill.py` for the shared skill. Do not run the CLI installer. The skill-only installer accepts the same `--client`, `--skills-dir`, and `--replace` options. The bundled `cli/skills/SKILL.md`, named `pixverse-api-cli`, is a CLI-specific guide and does not replace the shared skill.
6. Preserve existing MCP client settings when adding the selected remote connection. Use the HTTP type and header environment-variable syntax supported by that client; clients do not necessarily accept the same `type` value or interpolation syntax. Users configure credentials locally. Do not read authentication files, print keys, or ask users to send keys in chat.
7. Verify MCP connectivity and tool discovery without calling generation, deletion, or other business write tools. Installation does not authorize paid showcase reproduction. Follow the user's separately authorized scope for any business calls.
8. Copied files prove installation, not discovery. Start a new session outside the source repository and load `pixverse-api` through the client's native skill tool or a skill path discovered by that client. Reading the source repository, giving a generic capability answer, or using a built-in VideoGen tool does not verify the installed skill. Until this is actually checked, report "installed; new-session loading verification pending" rather than claiming discovery succeeded.

## Installation report

Report the integrations actually installed, CLI version, skill installation path, MCP connectivity and discovery results, and any missing configuration. Keep unfinished items explicit when credentials are missing, a connection is disabled, or the client has not discovered the skill.

The shared skill offers a one-line showcase suggestion when users identify themselves as beginners or ask for examples. It does not require users to view examples first. See `skills/pixverse-api/SKILL.md` for the shared workflow.
