# Development Guide

[Home](../README.md) · [Installation](installation.md) · [CLI guide](cli.md) · [MCP guide](mcp.md)

The CLI and MCP service use independent Python packages. Shared skill instructions route assistants to either integration; runtime code does not require one integration to invoke the other.

## Repository layout

| Path | Purpose |
|---|---|
| `cli/` | Production OpenAPI command-line client and packaged input contracts. |
| `skills/pixverse-api/` | Shared assistant skill and its CLI, MCP, and showcase references. |
| `scripts/` | CLI and skill installers. |
| `tests/` | Offline CLI and installation regression tests. |
| `docs/` | English installation, usage, and development guides. |

## CLI development

From the repository root:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" PIXVERSE_FORCE_INSTALLED=1 .venv/bin/python -m pytest -q tests
.venv/bin/ruff check cli scripts/install.py scripts/install_skill.py tests
.venv/bin/python -m build
```

The package exposes `pixverse-api` and includes its CLI-specific skill reference and input schema. Source distributions also contain both installers and the complete shared skill. Installation tests cover client detection, directory overrides, replacement, isolated CLI installation, and partial failures without making business API requests.

## Contribution checks

Write commit messages and Markdown in English, except for the root `README.zh-CN.md`. Keep the two README versions in the same section order. Update both when installation commands, authentication, or capabilities change; endpoint URLs and user-facing examples may be localized.

Keep detailed instructions in these guides and the README focused on getting started. Preserve the complete shared skill and client-native directory rules when changing installation. Verify native skill loading in a fresh session separately from file installation.

Run relevant offline checks before reporting success. Do not treat task acceptance, a copied skill, a build, or a deployment as evidence of completed business acceptance. Paid tasks require a separately authorized test scope.
