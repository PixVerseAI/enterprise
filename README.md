# PixVerse Enterprise

English | [简体中文](README.zh-CN.md)

Create and edit videos with PixVerse through a command-line client, remote MCP, and a shared skill for AI assistants.

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

See the [installation guide](docs/installation.md) for client skill directories, overrides, and new-session checks.

## CLI quick start

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository, then run from its root:

```bash
git clone https://github.com/PixVerseAI/enterprise.git
cd enterprise
python3 scripts/install.py
pixverse-api --help
```

Provide your API key through `PIXVERSE_API_KEY` in your local environment, then check your balance:

```bash
pixverse-api --json account balance
```

The CLI uses the production API at `https://app-api.pixverse.ai` by default. Keep keys out of chat and source control.

See the [CLI guide](docs/cli.md) for commands, parameters, and task results.

## MCP quick start

Connect to **https://app-api.pixverse.ai/opanapi/mcp** with a client supporting **Streamable HTTP** and custom headers. No local MCP server or CLI installation is required.

Set `PIXVERSE_OPENAPI_KEY` in the client process's environment. Example for Pi:

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

Other clients may use different configuration fields or variable syntax. Install the shared skill with `python3 scripts/install_skill.py`, then reload or reconnect your client. Ask it to check your balance to verify authentication; discovering tools alone does not verify the key.

See the [MCP guide](docs/mcp.md) for client configuration, tool schemas, and task handling.

## Examples and documentation

- [Showcase](skills/pixverse-api/references/showcase.md) — original assets, prompts, settings, and example videos.
- [Installation guide](docs/installation.md)
- [CLI guide](docs/cli.md)
- [MCP guide](docs/mcp.md)
- [Development guide](docs/development.md)
- [Platform API documentation](https://docs.platform.pixverse.ai/)

Generation may consume credits. A submitted task is not a completed video; query the returned task ID before reporting a result.
