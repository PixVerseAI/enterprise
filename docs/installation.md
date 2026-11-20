# Installation Guide

[Home](../README.md) · [CLI guide](cli.md) · [MCP guide](mcp.md)

## Choose an integration

| Request to your assistant | Installation |
|---|---|
| Install the repository, project, plugin, or CLI | CLI + shared `pixverse-api` skill |
| Install or connect MCP | Remote MCP + shared `pixverse-api` skill |
| Install both CLI and MCP | Both integrations + one shared skill |

The shared skill guides either CLI or MCP use. The bundled `cli/skills/SKILL.md`, named `pixverse-api-cli`, is a CLI-specific reference and does not replace the shared skill. Reading or developing this repository does not itself request installation. See [agent instructions](../AGENTS.md) for the full installation contract.

## Install CLI and skill

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/). Clone the repository and run from its root:

```bash
python3 scripts/install.py
pixverse-api --version
pixverse-api --help
```

The installer uses `uv tool install` to build the original package in an isolated Python environment. It installs the complete shared skill, including `references/`, for the current client. It does not require a PixVerse key, configure MCP, or make business API calls.

The installer identifies the current client from its parent process before considering client environment settings. When automatic detection is unavailable but the client identity is known, select it explicitly:

```bash
python3 scripts/install.py --client opencode
```

Supported client values are `workbuddy`, `deepseek`, `opencode`, and `pi`. Multiple client environment settings do not mean all clients should be installed.

## Client skill directories

Each path is a **parent directory**; installation creates `pixverse-api/` beneath it. Configured overrides take precedence over defaults.

| Client | Default global skill directory | Directory override |
|---|---|---|
| WorkBuddy CLI | `~/.codebuddy/skills/` | `$CODEBUDDY_CONFIG_DIR/skills/` |
| DeepSeek Harness | `~/.dsh/skills/` | `$DSH_HOME/skills/` |
| OpenCode | `~/.config/opencode/skills/` | `$XDG_CONFIG_HOME/opencode/skills/` |
| Pi | `~/.pi/agent/skills/` | `$PI_CODING_AGENT_DIR/skills/` |

WorkBuddy's model/settings directory is not its skill directory. `WORKBUDDY_CONFIG_DIR` must not be substituted for `CODEBUDDY_CONFIG_DIR`. `OPENCODE_CONFIG` selects a configuration file, not a skill root; check OpenCode's configuration directory with `opencode debug paths config`.

For another client or a custom native skill directory, pass its parent path explicitly:

```bash
python3 scripts/install.py --skills-dir /absolute/path/to/skills
```

An identical installed skill is left unchanged. Review a different installed version before adding `--replace`; replacement backs up the previous version outside the client's skill discovery directory.

Directory references: [CodeBuddy directories](https://www.codebuddy.ai/docs/cli/codebuddy-dir), [DeepSeek skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md), [OpenCode skills](https://opencode.ai/docs/skills/).

## Install MCP and skill only

Clone this repository and run the MCP-only installer. It configures the current client and installs the **complete repository-original** `pixverse-api` skill in one operation:

```bash
python3 scripts/install_mcp.py
# DeepSeek: select the profile actually running this session.
python3 scripts/install_mcp.py --client deepseek --profile headless
# Explicit China service selection, in any prompt language:
python3 scripts/install_mcp.py --region cn
```

This command does not install the CLI, read an API key, or call business APIs. It accepts `--client` and `--replace`; review conflicting existing settings before replacement. The original five skill files are copied and checked, not synthesized by the assistant. `scripts/install_skill.py` remains available when only the skill is needed, including manually configured clients.

Endpoint choice is explicit and language-independent. With no service selection, use `global` (`https://app-api.pixverse.ai/opanapi/mcp`). Use `--region cn` for an explicit China request or when explicitly following the Chinese README's service setup (`https://app-api.pixverseai.cn/opanapi/mcp`). Do not infer the service from Chinese/English text, locale, or model provider. Supply the selected service's key through `PIXVERSE_OPENAPI_KEY`. Rerunning with another region updates the `pixverse` connection; do not add a second enabled alias or retry another region after authentication failure.

WorkBuddy writes `$CODEBUDDY_CONFIG_DIR/.mcp.json` (default `~/.codebuddy/.mcp.json`), not the model directory. Pi writes `$PI_CODING_AGENT_DIR/mcp.json`. OpenCode uses the explicit `$OPENCODE_CONFIG` file when set, otherwise its native global configuration under `$XDG_CONFIG_HOME/opencode/`, with its installed major version's MCP structure. Its skill directory remains under `$XDG_CONFIG_HOME/opencode/skills/` even when the configuration file is elsewhere. DeepSeek adds an `insert` entry to `$DSH_HOME/profiles/<profile>/cordis.patch.yml`; a bare id override does not register a new plugin. Existing unrelated settings are retained. Unsupported JSONC or conflicting profile entries stop with an error instead of silently overwriting them.

Preserve existing client settings when adding MCP. Configure the endpoint and credentials using the client's supported HTTP fields and environment-variable syntax. A successful connection and tool discovery do not verify API authentication; use a balance query when authorized.

## Installation telemetry

The CLI and MCP installers attempt to send one installation report to PixVerse Platform in the background after every installation attempt. Platform forwards the report to Sensors Analytics. The report includes the installer version, a random attempt ID, the integration (`cli` or `mcp`), the detected client category, the action, the outcome, the elapsed time, and applicable CLI version, PATH status, skill status, MCP region, or fixed error code. Reports omit credentials, paths, and raw installer output. Delivery failures do not change the installation result. The standalone skill installer sends no report.

## Verify a new session

Start a new assistant session outside the source repository and ask about PixVerse. Verify that the client discovers and loads the installed `pixverse-api` skill through its native skill mechanism. Reading this repository's source files or receiving a generic answer is not proof that the installed skill loaded.

Report the CLI version, installed skill path, and any pending connection or loading checks. No paid generation task is needed. The skill may offer a one-line [showcase](../skills/pixverse-api/references/showcase.md) suggestion to beginners; viewing examples is optional. Examples include direct CDN links to assets and videos.

## Troubleshooting

| Symptom | Action |
|---|---|
| Client cannot be detected | Use the known `--client` value or the client's native `--skills-dir`. |
| uv is missing | Install it using the official instructions above, then rerun the installer. |
| CLI installed but not found | Add the bin directory reported by the installer to `PATH`. |
| CLI or skill installation partially failed | Review the reported completed steps, resolve the failure, then rerun. Do not report both integrations as installed. |
| Existing skill differs | Review it, then explicitly use `--replace` if replacement is intended. |
| Skill is copied but absent from a session | Check the native directory and start a new session; copied files alone do not prove discovery. |
| Header contains an unexpanded variable | Check the client's interpolation syntax and whether the variable exists in the client process. |

Do not work around an old system pip by disabling build isolation or editing packaging metadata. Do not send keys in chat or read authentication files into the assistant's context.
