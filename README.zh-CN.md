# PixVerse Enterprise

[English](README.md) | 简体中文

通过命令行、远程 MCP 和面向 AI 助手的共享 Skill，使用 PixVerse 生成和编辑视频。

## 功能概览

- 文生视频、图生视频、首尾帧生成和多引用融合。
- 编辑视频、添加音效、提高清晰度，以及生成数字人和口型同步视频。
- 使用模板、电商广告、音乐视频和自定义音色。
- 上传素材、查询积分与用量，以及查询任务。

具体能力和支持的参数取决于 API 及账号权限。

## 让 AI 助手安装

把这句话发给你的助手：

> 帮我安装 https://github.com/PixVerseAI/enterprise 。

默认安装 **CLI 和共享的 `pixverse-api` Skill**。明确要求接入 MCP 时，则配置 **远程 MCP 并安装同一份 Skill**。Skill 同时支持两种接入方式。

客户端 Skill 目录、路径覆盖和新会话验证见[安装指南](docs/installation.md)（英文）。

## CLI 快速开始

需要 Python 3.10+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。克隆仓库后，在根目录执行：

```bash
git clone https://github.com/PixVerseAI/enterprise.git
cd enterprise
python3 scripts/install.py
pixverse-api --help
```

在本地环境中设置 API Key 变量 `PIXVERSE_API_KEY`，然后查询余额：

```bash
pixverse-api --region cn --json account balance
```

使用 `--region cn` 选择生产 API：`https://app-api.pixverseai.cn`。不要把 Key 发到聊天或提交到代码仓库。

完整命令、参数和任务结果说明见 [CLI 指南](docs/cli.md)（英文）。

## MCP 快速开始

通过支持 **Streamable HTTP** 和自定义请求头的客户端，连接 **https://app-api.pixverseai.cn/opanapi/mcp**。无需运行本地 MCP 服务，也无需安装 CLI。

在客户端进程环境中设置 `PIXVERSE_OPENAPI_KEY`。以下为 Pi 配置示例：

```json
{
  "mcpServers": {
    "pixverse": {
      "type": "http",
      "url": "https://app-api.pixverseai.cn/opanapi/mcp",
      "headers": {
        "Authorization": "Bearer ${PIXVERSE_OPENAPI_KEY}"
      }
    }
  }
}
```

其他客户端的字段或变量语法可能不同。执行 `python3 scripts/install_skill.py` 安装共享 Skill，再重新加载或连接客户端。让助手查询余额以确认鉴权；仅发现工具不能证明 Key 有效。

客户端配置、工具 Schema 和任务处理说明见 [MCP 指南](docs/mcp.md)（英文）。

## 示例与文档

- [Showcase](skills/pixverse-api/references/showcase.md)：包含原始素材、提示词、参数和成片示例（英文）。
- [安装指南](docs/installation.md)（英文）
- [CLI 指南](docs/cli.md)（英文）
- [MCP 指南](docs/mcp.md)（英文）
- [开发指南](docs/development.md)（英文）
- [开放平台 API 文档](https://docs.platform.pai.video/)

生成任务可能消耗积分。提交成功不代表视频已经完成，应查询返回的任务 ID 后再确认结果。
