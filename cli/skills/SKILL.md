---
name: pixverse-platform
description: 使用 pixverse-api CLI 在国内或海外生产开放平台上传素材、查询余额、生成和编辑视频，以及调用电商 Native/Template 和统一 V3 MV。
---

# PixVerse Platform

使用已安装的 `pixverse-api`；根选项 `--region global|cn` 选择对应生产 API，默认 `global`，不读取地区环境变量。API Key 仅通过 `PIXVERSE_API_KEY` 提供。凭据由用户自行在运行环境配置；不要读取认证文件、打印Key或把Key放进参数、文档。只使用同地区、同账号资源。

先读子命令的 `--help`。全局 `--region`、`--json`、`--timeout` 放在子命令之前。成功JSON在stdout，错误在stderr；退出码2为配置/输入错误，1为请求错误或任务失败终态。

## 命令选择

- 余额/上传：`account balance`、`image upload`、`media upload`。上传的`--file`与`--url`二选一。URL使用HTTPS，端口为默认或443，不含内嵌凭据、片段或空白；不限制供应商域名。
- 用量：`account usage`查询当前Key的消耗/返还明细。首次给start-time/end-time，国内UTC+8、海外UTC，左闭右开；时间窗口和日期先后由Platform校验；可重复creation-type/credits-status，每次一页，续页只原样传cursor。
- 视频模板：`template list`只查视频，支持template-id/mode/page/page-size；`template generate --id`先读元数据再提交，纯视频输出限定。传统模板必填model/duration/quality，单图或按顺序重复img-id；Workflow只用重复input JSON，每项input_key及一种text/img_id/video_media_id/source_video_id/audio_media_id。文字默认值和动态input_limit由Platform校验；先查当前可用模板，不猜节点key，不跨地区回退。
- 基础T2V/I2V支持webhook-id及negative-prompt；具体模型组合由服务端校验，不把省略选项变成显式默认值。
- 基础生成：`video generate`（T2V）、`video from-image`（I2V）、`video f2v`、`video fusion`。I2V提示词可省略，填写时最多5000字符；画幅沿用图片，不提供比例选项。
- 音效：`video sound-effect`，视频来源二选一，可选sound-effect-content和original-sound开关；不传模型或清晰度。
- 多帧转场：`video multi-transition`默认V5，按顺序重复至少两个`--frame` JSON；每段duration属于起始帧，末帧省略或填0。帧数上限、分段及总时长由Platform校验，CLI不改写。
- 编辑：`video extend`、`expand`、`upscale`、`restyle`、`mimic`、`swap`、`modify`。
- 数字人：`video lipsync`、`video avatar`。音频`--audio-media-id`与TTS参数组`--tts-speaker-id/--tts-content`严格二选一。Avatar支持360p/540p/720p/1080p，可选prompt上限2048字符；Avatar TTS要求30–200个Unicode码点，由Platform校验实际文本。
- 前置查询：`voice list`、`video restyle-list`、`video mask`。
- 自定义音色：上传最长30秒语音样本，再`voice create --name ... --audio-media-id ...`；`voice list --type custom|system|all --scene avatar|lip_sync`使用新列表及试听字段，省略type默认all，每页20条；page-size仅10/20/50/100，全部走新版音色列表。用返回custom_音色ID供LipSync/Avatar等TTS输入；`voice delete --speaker-id ...`只删除明确指定的自定义音色，不自动重试。
- 电商只使用`agent ecommerce-native`（414562414124107）或`agent ecommerce-template`（414562414124108）；不替换成其他Agent。需要至少一种非空图片引用、prompt、15/30/45/60秒和language-code；图片数量及avatar有效性由Platform校验；Template另需video-style。
- 电商`--image-ref`支持img_id/ref_name并保留引用名，与`--img-id`二选一。TTS数字ID不跨地区假设音色相同，先按`voice list`核对名称和语言。
- MV：`agent mv`固定`vibe_mv_v3_custom`。上传音频后直接提交，服务端异步校验依赖目标地域后端部署；可传角色图、Custom风格图、歌词时间戳和preserve-outfit。

## 资源与参数

视频来源必须且只能提供`--source-video-id`或`--video-media-id`。Mask的keyframe-id可省略，不注入默认帧；命令同步返回结果，不是video_id；Swap使用相同源视频及同次Mask响应的keyframe_id与字符串mask_id。Modify重复`--mask-id`和`--img-id`时保留顺序；Mask ID需要显式keyframe-id。

Fusion可重复`--img-id`，或重复`--image-ref` JSON对象提供img_id/type/ref_name；视频参考用`--video-ref`。支持V6 Omni和aspect-ratio=auto；图片模式显式填正秒，Omni视频模式显式填0，省略duration时不注入值。模型组合、引用数量和名称有效性由Platform校验。

MV角色图与风格图各最多1张，风格图只用于Custom；Custom至少有一种参考图。新风格由服务端校验，不使用过时枚举替换用户选择。歌词文件形如`{"words":[{"start":0,"end":0.5,"word":"你好"}]}`；start/end必须是非负有限数值，顺序、不重叠、字数及真实音频时长匹配由Platform校验。显式`--no-caption`、`--no-lip-sync`、`--no-preserve-outfit`会保留false。

## 提交与查询

创建可能消耗真实生产点数，仅在用户授权后执行。创建响应的`submission=accepted`和`response.Resp.video_id`表示受理；默认只报告ID，只有用户要求等待/监控时才主动查询。查询使用`pixverse-api --region <本次地区> --json video get --id <video_id>`，查询沿用创建时的地区，可直接使用返回的 `query_command`；不要重新创建。

Workflow模板创建返回`response.Resp.task_id`，使用`pixverse-api --region <本次地区> --json template get --id <task_id>`；不要把task_id当video_id。成功视频链接汇总在output_urls，只有一条时另有output_url。图片/混合输出及既有排除Agent不因模板入口扩大接入范围。

`task_status`同时归一化普通数字状态和Agent的running/succeeded/failed状态。成功结果统一在`output_url`，原协议保留在response中。`output_url_verified=false`表示CLI没有探测链接，不据此声称成片可访问。网络超时可能已经创建任务，禁止直接重试写请求。`Resp.credits`不替代最终扣费账本。

JSON还包含`stage`和`submission_state`：本地校验或模板发现失败为`not_submitted`，Platform业务拒绝为`rejected`，确认写入为`accepted`，写入超时或成功响应缺少有效ID等不确定结果为`unknown`；只读为`not_applicable`。`unknown`不代表未受理或未扣费，禁止直接重发。失败终态`ok=false`且退出码1。输入错误提供字段、约束和允许值；上游公开错误保留在error.response并脱敏。

CLI仅校验打包的公开契约；模型可用性、数量、权限、审核、计费和动态模板规则由Platform处理，不自行降级模型或省略用户要求。
