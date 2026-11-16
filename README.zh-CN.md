# PixVerse Enterprise

[English](README.md) | 简体中文

PixVerse Enterprise 提供生产 OpenAPI 命令行工具、面向 AI 助手的 Skill 及远程 MCP 接入说明。支持基础生成、视频模板、多帧转场、音效、视频编辑、数字人、电商 Agent、V3 MV 及 Key 级用量明细。CLI 入口为 `pixverse-api`，需要 Python 3.10+。

可用能力、模型和参数以开放平台文档及账号权限为准。

| 目录 | 用途 |
|---|---|
| `cli/` | 生产 OpenAPI 命令行客户端。 |
| `skills/` | AI 助手使用 CLI 的操作说明。 |

## 安装

在项目目录执行：

```bash
pipx install .
pixverse-api --region cn --help
```

开发安装与验证：

本仓库的所有 Git 提交信息必须使用英文。

```bash
uv venv .venv
uv pip install --python .venv/bin/python -e '.[dev]'
PATH="$PWD/.venv/bin:$PATH" PIXVERSE_FORCE_INSTALLED=1 .venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/python -m build
```

## 配置

CLI 通过根选项 `--region cn` 选择本页的生产 API；省略 `--region` 时默认 `global`，不再读取地区环境变量。进程环境只需提供 `PIXVERSE_API_KEY`（自己的生产 API Key）。请用终端环境或凭据管理器注入 Key，不在命令参数、聊天或源码中填写。CLI 不读取 `.env`、个人 Skill 认证配置或配置文件，不写入 Key。

生产 API 地址固定为 `https://app-api.pixverseai.cn`。

缺少或无效的配置会在发请求前报错。请使用同一 API 入口、同一账号下的 Key、素材和任务 ID。CLI 没有 `--env` 或 `--base-url`，不跟随重定向，不读取系统代理变量。

## 远程 MCP 接入

远程 MCP 地址为 `https://app-api.pixverseai.cn/opanapi/mcp`。使用支持 Streamable HTTP 和自定义请求头的 MCP 客户端即可接入，无需安装本地服务或 CLI。

在启动 MCP 客户端前，通过其进程环境提供自己的 API Key，变量名统一为 `PIXVERSE_OPENAPI_KEY`。Pi 等支持 `${变量名}` 展开的客户端可使用以下配置：

```json
{
  "mcpServers": {
    "pixverse-enterprise": {
      "url": "https://app-api.pixverseai.cn/opanapi/mcp",
      "headers": {"Authorization": "Bearer ${PIXVERSE_OPENAPI_KEY}"}
    }
  }
}
```

环境变量由 MCP 客户端展开；若客户端采用其他语法或安全凭据存储，请按其支持的方式配置同一 Bearer 认证请求头，不要将真实 Key 写入 JSON 文件或提交到源码仓库。设置环境变量后再启动客户端；已有 Pi 会话修改配置文件后可输入 `/reload` 加载。

工具使用当前连接的 PixVerse 账户。服务地址和自己的 API Key 在客户端配置；结果返回业务数据和排查所需的追踪标识，不附带部署标签。本版使用 API Key 认证，不提供 OAuth 登录。可先调用 `account_balance` 检查认证结果，工具列表可见不代表 Key 有效。

素材上传及 Mask URL 按工具协议校验，无需配置供应商域名白名单。MCP 保留必填、类型、枚举和正式互斥依赖等协议校验；动态模型/模板能力、素材有效性、权限与审核交给 Platform，不读取客户端本地文件。生成可能消耗积分，提交成功仅表示受理；请使用对应查询工具确认状态。服务不自动重试写操作或轮询任务。

工具声明完整列出可用字段以兼容客户端展示；服务端仍按完整规范执行互斥和依赖校验。每项工具提供 `pixverse://contracts/<工具名>/input-schema` 契约资源，可通过 MCP resources 读取。服务更新后请重新连接或加载客户端，刷新缓存的工具声明。

调用以 `tools/list` 中的 MCP 参数名为准，REST 示例可能使用映射前的名字：

| 场景 | MCP 参数或查询工具 |
|---|---|
| V3 自定义 MV | `audio_media_id`、单个 `img_id`、`mv_prompt`、`mv_style`、`caption`、`lip_sync`、`preserve_outfit` |
| Native / Template 电商 | `language_code`，如 `zh-CN`；Template 还需枚举内的 `video_style` |
| 创建音色 / 使用 TTS | 用 `name`、`audio_media_id` 创建；将返回的 `speaker_id` 作为 Avatar 或 LipSync 的 `tts_speaker_id` |
| 查询音色 | `speaker_type` 省略或为 null 时查询 `all`；可用 `custom`、`system` 筛选。默认每页20条，仅支持10/20/50/100；全部走新版音色列表接口 |
| 模板元数据 | `template_list(template_ids=[...])`；`template_id` 不是执行任务 ID |
| 标准 / Workflow 结果 | 标准生成返回 `video_id` → `video_get`；Workflow 返回 `task_id` → `template_get` |

用户明确要求的人物、风格、引用和音频开关应保留在请求中；无法表达时先说明，不提交缩水请求。受理后沿用同一任务 ID，不因耗时长重新生成。用户未要求持续观察时只查询一次；需要长期观察时使用客户端等待能力及上游已有重试建议，避免紧密循环。重复查询状态与重复创建任务不同，客户端提示“可能重复”本身不能证明重复生成，也不应通过改参数规避提示。

Avatar 支持 `360p`、`540p`、`720p`、`1080p`，可选 prompt 上限2048字符；TTS 要求30–200个 Unicode 码点（最小值按去除首尾空白后计，最大值包含首尾空白），由 Platform 校验实际文本。Fusion 提供 V6 Omni 分支的 `aspect_ratio=auto`，具体模型与素材组合由 Platform 判定；空引用数组不转发。省略 Fusion duration 或 Mask keyframe 时不注入值，显式 `0`、`false` 保留。后续编辑复用 Mask 实际返回的关键帧与 mask。

31个工具均声明 `outputSchema`，返回的 JSON 文本与 `structuredContent` 一致。Pi 1.5.2 codemode 等保留 MCP 返回外壳的客户端，业务结果位于 `result.structuredContent`；已解包的客户端直接返回业务对象。可用 `const data = result.structuredContent ?? result` 取值，无需再次解析 JSON 字符串。原始业务扩展字段保留在 `response` 或 `error.response` 并脱敏。请检查 `ok`、`stage`、`submission_state`：写入前的校验或元数据查询失败为 `not_submitted`，Platform 明确拒绝为 `rejected`，确认写入为 `accepted`，写入超时、成功响应缺少有效 ID 等无法确认的结果为 `unknown`；只读调用为 `not_applicable`。`accepted` 不表示生成完成，`unknown` 不表示未扣费，不应自动重发；请保留 TraceId 核查。查询结果的 `output_url_verified=false` 表示服务没有探测链接。

协议错误会指出字段、失败约束及声明的允许值；Platform 错误详情保留并脱敏。

## 命令

```bash
# 查询余额
pixverse-api --region cn account balance
pixverse-api --region cn --json account balance

# 图片上传；--file 与 --url 二选一
pixverse-api --region cn image upload --file /absolute/path/image.png
pixverse-api --region cn image upload --url https://example.com/image.png

# 视频/音频上传
pixverse-api --region cn media upload --file /absolute/path/video.mp4
pixverse-api --region cn media upload --url https://example.com/audio.wav

# 文生视频（默认 v6、5 秒、720p、16:9）
pixverse-api --region cn video generate --prompt "一只猫走过草地" --no-audio

# 图生视频；将下面示例 ID 替换成同地区、同账号上传返回的 img_id
pixverse-api --region cn video from-image --img-id 123456 --prompt "让主体缓慢向前走" --no-audio

# 单次查询；将示例 ID 替换成创建响应中的 video_id
pixverse-api --region cn --json video get --id 123456
```

基础 T2V/I2V 命令支持 `--model`、`--duration`、`--quality`、`--seed`、`--audio/--no-audio`、`--multi-clip/--no-multi-clip`、`--webhook-id`和`--negative-prompt`；文生视频另外支持 `--aspect-ratio`。音频、多镜头选项省略时不发送该字段，使用服务端默认。模型、权益和参数组合由服务端作最终校验；不提供任意请求JSON透传。

图片上传使用 multipart 的 `image` / `image_url`；视频音频使用 `file` / `file_url`。文件以流式方式发送，格式、大小、时长及审核由 API 校验。CLI 不下载远程素材，仅把 URL 交给官方上传接口。

## 用量明细与视频模板（0.4.0）

`account usage`查询当前API Key的消耗/返还记录，不把创建响应中的报价当成最终流水。首次查询必填开始、结束时间，默认50条、最多100条，时间范围左闭右开且最多30天。时间格式为`YYYY-MM-DD HH:MM:SS`，按UTC+8解释；可重复传`--creation-type`和`--credits-status consume|refund`。只查询一页；续页原样传`next_cursor`，不能混用其他条件。游标绑定原Key与API入口。

```bash
pixverse-api --region cn --json account usage --start-time '2026-11-01 00:00:00' --end-time '2026-11-02 00:00:00' \
  --creation-type text_to_video --credits-status consume --credits-status refund --limit 20
pixverse-api --region cn --json account usage --cursor '替换为上一页next_cursor'
```

`template list`固定查询视频模板（type=1），支持重复`--template-id`、`--mode standard|workflow`、页码及10/20/50/100条分页，保留输入、时长、清晰度、价格和输出元数据。可用模板以实际列表响应为准。`template generate`每次先精确读取所选模板元数据，再单次提交，不绕过模板和账号权限。

传统模板必须显式指定`--model`、`--duration`、`--quality`，按模板配置选择组合；单图传一次`--img-id`，多图按顺序重复传入。无图片的单图类模板使用文生入口并须给prompt，可选aspect-ratio。具体图数由服务端最终校验。Workflow模板只接受重复`--input`具名JSON对象，input_key从列表复制，每项仅提供text/img_id/video_media_id/source_video_id/audio_media_id中的一种；文字省略时采用模板默认。仅生成纯视频输出，图片和混合输出模板不接入。

```bash
pixverse-api --region cn --json template list --mode standard --page 1 --page-size 20
pixverse-api --region cn --json template list --template-id 123
pixverse-api --region cn --json template generate --id 123 --img-id 11 --model v5.6 --duration 5 --quality 720p
pixverse-api --region cn --json template generate --id 124 --img-id 11 --img-id 12 --model v5.6 --duration 5 --quality 720p
pixverse-api --region cn --json template generate --id 125 \
  --input '{"input_key":"替换为图片节点key","img_id":11}' \
  --input '{"input_key":"替换为文字节点key","text":"商品展示"}'
```

传统模板响应是`video_id`，沿用`video get --id`；Workflow响应是独立`task_id`，使用`template get --id`。后者保留`Resp.contents`并仅从成功视频输出汇总`output_urls`；只有一条时额外提供`output_url`，不会把中间产物当成成片。统一退出码、未验证URL标记、不自动轮询/重试/下载规则同样适用。

```bash
pixverse-api --region cn --json video get --id 123456
pixverse-api --region cn --json template get --id 234567
pixverse-api --region cn video generate --prompt '商品转台展示' --webhook-id 123 --negative-prompt 'blur'
```

## 视频扩展、音效与编辑

以下 ID 均为示例，必须替换为同账号、同地区的真实上传/生成结果。

| 能力 | 命令 | 主要输入 |
|---|---|---|
| F2V | `video f2v` | `--first-frame-img`、`--last-frame-img`、`--prompt` |
| SoundEffect | `video sound-effect` | 视频来源；可选`--sound-effect-content`、`--original-sound/--no-original-sound` |
| MultiTransition | `video multi-transition` | 按顺序重复`--frame` JSON，默认V5；末帧duration省略或0 |
| Fusion | `video fusion` | 重复 `--img-id` 或 `--image-ref`；支持 Omni `--video-ref` |
| Extend | `video extend` | 视频来源、`--prompt`、延长时长 |
| Expand | `video expand` | 视频来源、`--aspect-ratio`，输出720p/1080p |
| Upscale | `video upscale` | 视频来源 |
| Restyle | `video restyle` | 视频来源、`--restyle-id` / `--restyle-prompt`二选一 |
| LipSync | `video lipsync` | 视频来源、音频 / TTS二选一 |
| Avatar | `video avatar` | `--img-id`、音频 / TTS二选一，输出360p/540p/720p/1080p |
| Mimic | `video mimic` | 视频来源、`--img-id`，可选`--post-reference image\|video` |
| Mask | `video mask` | 视频来源、可选`--keyframe-id`，同步返回Mask列表 |
| Swap | `video swap` | 同源视频、Mask响应中的关键帧和字符串Mask ID、替换图 |
| Modify | `video modify` | 视频来源、`--prompt`，可选多图/多Mask |

“视频来源”必须且只能提供 `--source-video-id`（平台已生成视频）或 `--video-media-id`（上传视频）。生成命令沿用统一 `video get --id` 查询。Mask同步返回结果，不能当作视频创建任务查询；CLI不会自动选区。

```bash
pixverse-api --region cn video f2v --first-frame-img 11 --last-frame-img 12 --prompt "从清晨过渡到黄昏"
pixverse-api --region cn video fusion --img-id 11 --img-id 12 --prompt "两个主体自然互动"
pixverse-api --region cn video fusion --reference-mode omni --video-ref '{"video_media_id":22}' --prompt "参考动作和运镜"
pixverse-api --region cn video extend --source-video-id 21 --prompt "继续向前移动" --duration 5
pixverse-api --region cn video expand --video-media-id 22 --aspect-ratio 9:16 --quality 720p
pixverse-api --region cn video upscale --source-video-id 21
pixverse-api --region cn video restyle --video-media-id 22 --restyle-prompt "柔和水彩风格"
pixverse-api --region cn video lipsync --video-media-id 22 --audio-media-id 41
pixverse-api --region cn video avatar --img-id 11 --tts-speaker-id Auto --tts-content "欢迎使用开放平台"
pixverse-api --region cn video mimic --img-id 11 --video-media-id 22 --post-reference video
pixverse-api --region cn --json video mask --video-media-id 22 --keyframe-id 0
# 将关键帧和mask-id换为上一条Mask响应，保持视频来源一致；"0"是合法字符串ID
pixverse-api --region cn video swap --video-media-id 22 --keyframe-id 0 --mask-id 0 --img-id 12
pixverse-api --region cn video modify --video-media-id 22 --prompt "将主体替换为参考图" --img-id 12 --mask-id 0 --keyframe-id 0
pixverse-api --region cn voice list
pixverse-api --region cn video restyle-list
```

Fusion 的 `--image-ref` 接受单个JSON对象，可重复传入，字段为 `img_id`、可选 `type/ref_name`；`--video-ref`每项只提供一种视频来源及可选`ref_name`。支持V6 Omni和`--aspect-ratio auto`。图片模式显式填写正秒，Omni视频模式显式填写0；省略duration时不注入值，显式值原样保留。模型/素材组合、引用数量及名称有效性由Platform校验。

SoundEffect给已有视频生成音效，视频来源二选一；省略内容时由服务端自动生成，不需要模型或清晰度参数。MultiTransition接受至少两个`--frame`对象（img_id、可选prompt、duration）；每段duration属于起始帧，末帧省略duration或设0。帧数上限、分段/总时长及模型组合由Platform校验，CLI不改写。例如：

```bash
pixverse-api --region cn --json video sound-effect --video-media-id 123 --sound-effect-content 'gentle rain' --no-original-sound
pixverse-api --region cn --json video multi-transition --model v5 --quality 720p \
  --frame '{"img_id":11,"duration":5,"prompt":"sunset"}' \
  --frame '{"img_id":12,"duration":5,"prompt":"night"}' \
  --frame '{"img_id":13}'
```

LipSync/Avatar使用 `--audio-media-id` 或同时提供 `--tts-speaker-id` 与 `--tts-content`，不可混用。Mimic/Swap/Modify输出不支持1080p。Modify可重复`--img-id`和`--mask-id`并保留顺序；用Mask ID时必填`--keyframe-id`。也支持重复`--mask-url`，与Mask ID二选一。只有Modify支持自备Mask URL，Swap只接受Mask ID。Mask请求仅发送视频来源和关键帧，不提供`mask_prompt`选项。

## 电商 Agent 与最新 MV

MV当前仅暴露V3 Custom，不提供Beat Mix、Visual Riff或任意mv_agent_type覆盖。

电商只开放两个明确的子命令，不提供任意 `agent_id` 覆盖：

| 命令 | 固定 agent_id | 补充要求 |
|---|---|---|
| `agent ecommerce-native` | `414562414124107` | 至少一种非空图片引用、prompt、duration、language-code |
| `agent ecommerce-template` | `414562414124108` | 同上，另必填video-style |

时长为15/30/45/60秒，清晰度720p/1080p，默认9:16。Template的风格是`polished_commercials`、`personal_review`、`no_personal_review`；Native不接收该选项。可用`--avatar Auto`或模特图片ID字符串，`no_personal_review`场景的avatar由服务端忽略。配音、背景音乐、字幕通过`--lip-sync/--no-lip-sync`、`--bgm/--no-bgm`、`--caption/--no-caption`显式控制，省略则使用服务端默认。

支持重复`--image-ref '{"img_id":11,"ref_name":"product"}'`，保留商品图片引用名称；与`--img-id`二选一，引用只支持`img_id/ref_name`，图片数量和avatar有效性由Platform校验。音色ID通过`voice list`查询，使用当前API入口实际返回的ID。

```bash
pixverse-api --region cn agent ecommerce-native --img-id 11 --prompt "展示商品特点" --duration 15 --language-code zh-CN
pixverse-api --region cn agent ecommerce-template --img-id 11 --prompt "展示商品特点" --duration 15 --language-code zh-CN --video-style polished_commercials
pixverse-api --region cn agent ecommerce-native --image-ref '{"img_id":11,"ref_name":"product"}' --prompt "展示商品特点" --duration 15 --language-code en-US
```

`agent mv` 固定采用 `mv_agent_type=vibe_mv_v3_custom`。上传音频后直接提交 MV，音频由服务端异步校验；该行为依赖目标地域的后端完成部署，受理成功不代表审核或生成成功。

```bash
pixverse-api --region cn agent mv --audio-media-id 41 --img-id 11 --mv-style "Gothic Halloween" --preserve-outfit --caption --lip-sync
pixverse-api --region cn agent mv --audio-media-id 41 --img-id 11 --style-img-id 12 --mv-style Custom --lyric-timestamp-file /absolute/path/lyrics.json
```

角色图和风格图各最多1张；风格图仅用于Custom，Custom至少有一种图片参考。可用`--mv-prompt`、`--music-style`、`--lyric-text`、`--caption`、`--lip-sync`、`--preserve-outfit`及对应`--no-*`选项，显式false会保留。MV风格、音乐风格交给服务端模板校验，不把旧文档枚举写死。音频长度、权限、审核及风格是否在线由服务端判断。

歌词时间戳文件格式为 `{"words":[{"start":0,"end":0.5,"word":"你好"}]}`，时间为秒，必须是非负有限数值。CLI校验公开对象结构；顺序、不重叠、字数及真实音频时长匹配由Platform校验。与`--lyric-text`同时传入时按服务端契约优先使用时间戳。

## 自定义音色（0.5.0）

上传不超过30秒的语音样本后，用`voice create`创建当前账号的自定义音色。列表支持`--type system|custom|all`、`--scene avatar|lip_sync`和10/20/50/100条分页，返回音色类型及服务端提供的试听地址；不传type时默认all，每页20条，全部走新版接口。音色ID只在原账号、原地域使用，创建数量、会员及样本限制由服务端校验。

```bash
pixverse-api --region cn media upload --file /absolute/path/voice-sample.wav
pixverse-api --region cn voice create --name '品牌音色' --audio-media-id 41
pixverse-api --region cn --json voice list --type custom --scene avatar --page-size 20
pixverse-api --region cn video avatar --img-id 11 --tts-speaker-id custom_返回的ID --tts-content '欢迎使用我们的平台'
pixverse-api --region cn voice delete --speaker-id custom_返回的ID
```

create同步返回speaker_id，不作为视频生成任务查询；delete只接受custom_标识，兼容后端成功Resp=null/{}，不自动重试。删除只影响指定的自定义音色，使用前核对ID。

## CLI 输出与自动化

全局选项放在子命令之前：`pixverse-api --region cn --json --timeout 60 account balance`。

成功 JSON 包含 `ok`、`region`、`environment`、`trace_id`、`http_status` 和原始协议结构 `response`。敏感字段递归脱敏。每次请求自动生成新的 UUID v4 `Ai-trace-id`；HTTP 状态与业务 `ErrCode` 同时检查，服务端 `Error` 详情保留在 `response` 中，并优先展示公开的错误说明。

JSON额外包含`stage`和`submission_state`：写入前的校验/模板发现失败为`not_submitted`，Platform明确业务拒绝为`rejected`，确认写入为`accepted`，写入超时或成功响应缺少有效ID等不确定结果为`unknown`；只读调用（含POST用量查询）为`not_applicable`。`unknown`不代表未受理或未扣费，禁止自动重发。

CLI独立打包公开输入契约，保留必填、类型、枚举、范围、互斥及依赖校验；模型和素材组合、模板input_limit、时间窗口、权限、审核及计费由Platform判定。素材URL和Mask URL使用HTTPS，端口为默认或443，不含内嵌凭据、片段和空白；不增加供应商域名白名单，仍支持本地文件上传。I2V提示词可选，上限5000字符，画幅沿用图片；Avatar支持360p/540p/720p/1080p，可选prompt上限2048字符。CLI不依赖MCP项目，离线回归检查 CLI 自身的输入契约。

生成创建响应额外带 `submission: accepted`，仅表示提交成功，默认不轮询、不自动下载、不自动重试。请求超时或连接中断时不能保证任务未创建，请先核查任务或联系支持，再决定是否重新提交。

查询命令额外带 `task_status`（`completed` / `generating` / `moderation_failed` / `failed` / `unknown`），兼容普通视频数字状态和电商工作流的`running/succeeded/failed`等字符串状态。原协议保留在`response`；成功时`output_url`统一取自`Resp.url`或`Resp.output.video`，不把中间产物当作成片。`output_url_verified: false`表示CLI没有额外探测URL。`Resp.credits`保留作请求级展示，不作为最终扣费账本。

| 退出码 | 含义 |
|---|---|
| `0` | 请求成功，或任务仍在生成中 |
| `1` | HTTP/业务/协议/网络失败，或任务终态为失败/拒审 |
| `2` | 配置或命令输入无效 |
| `130` | 用户中断 |

请求失败时 stdout 为空，错误写入 stderr；`--json` 下错误也是 JSON，输入错误提供字段、约束及声明的允许值。任务查询本身成功但任务终态失败时，查询数据仍写 stdout，`ok=false`并以退出码 `1` 返回，便于脚本检查失败详情。未知任务状态保留原值，不推断生成完成。

## 相关链接

- [开放平台 API 文档](https://docs.platform.pai.video/)

请求参数、可用模型、计费及权益以接口文档和实际返回为准。
