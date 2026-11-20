# PixVerse Enterprise

English | [简体中文](README.zh-CN.md)

Create and edit videos with PixVerse through a command-line client, remote MCP, and a shared skill for AI assistants.

## Make videos with an AI agent (OpenCode example)

https://github.com/user-attachments/assets/3c4c28e3-a026-4cbd-ba4a-ad8a508bfd25

## Overview

- Generate videos from text, images, first/last frames, or multiple references.
- Edit videos, add sound effects, improve resolution, and create speaking characters.
- Use templates, ecommerce ads, music videos, and custom voices.
- Upload assets, check credits and usage, and query tasks.

Availability and supported parameters depend on the API and your account.

## Install with an AI assistant

Give your assistant this request:

> Install https://github.com/PixVerseAI/enterprise for me.

By default, this installs the **CLI and the shared `pixverse-api` skill**. Explicitly ask to connect MCP to get **remote MCP and the same skill**. The skill works with either integration.

For an MCP request, the assistant should clone this repository and run `python3 scripts/install_mcp.py`. This configures its client and installs the original skill together; it must not write a substitute skill. Without an explicit service choice, the installer uses `global`, regardless of your message's language.

See the [installation guide](docs/installation.md) for client skill directories, overrides, and new-session checks.

## CLI quick start

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository, then run from its root:

```bash
git clone https://github.com/PixVerseAI/enterprise.git
cd enterprise
python3 scripts/install.py
pixverse-api --help
```

Provide your API key through `PIXVERSE_OPENAPI_KEY` in your local environment, then check your balance:

```bash
pixverse-api --json account balance
```

The CLI uses the production API at `https://app-api.pixverse.ai` by default. Keep keys out of chat and source control.

See the [CLI guide](docs/cli.md) for commands, parameters, and task results.

## MCP quick start

Connect to **https://app-api.pixverse.ai/opanapi/mcp** with a client supporting **Streamable HTTP** and custom headers. No local MCP server or CLI installation is required.

Clone the repository and run its MCP-only installer with Python 3.10+:

```bash
git clone https://github.com/PixVerseAI/enterprise.git
cd enterprise
python3 scripts/install_mcp.py
```

The installer supports WorkBuddy, DeepSeek Harness, OpenCode, and Pi, including their native configuration directories. For DeepSeek, add the active profile, for example `--profile headless`. It installs the complete original `pixverse-api` skill without installing the CLI. Set `PIXVERSE_OPENAPI_KEY` in the client process's environment, then start a new session and check tool discovery and skill loading. Ask it to check your balance when you want to verify authentication; discovering tools alone does not verify the key.

See the [MCP guide](docs/mcp.md) for client configuration, tool schemas, and task handling.

## Examples and documentation

- [Showcase](skills/pixverse-api/references/showcase.md) — original assets, prompts, settings, and example videos.
- [Installation guide](docs/installation.md)
- [CLI guide](docs/cli.md)
- [MCP guide](docs/mcp.md)
- [Development guide](docs/development.md)
- [Platform API documentation](https://docs.platform.pixverse.ai/)

Generation may consume credits. A submitted task is not a completed video; query the returned task ID before reporting a result.
