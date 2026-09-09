# 视频文案提取与 AI 内容分析平台

## 1. 文档说明

### 1.0 文档状态

| 项目 | 内容 |
|---|---|
| 文档类型 | 产品需求文档（PRD） |
| 当前版本 | 1.0 |
| 文档状态 | 可进入 MVP 开发 |
| 目标运行方式 | 本地 Python 服务 + 浏览器操作界面 |
| 数据持久化 | SQLite + 本地文件系统 |

本文档定义产品范围、用户行为、数据留痕和验收标准；具体模块拆分、代码接口、启动方式和测试方法以《开发文档.md》为准。

### 1.1 项目目标

构建一个本地部署、以本地目录为主要输入方式的视频内容处理平台，实现：

```text
扫描本地目录
    ↓
识别视频/音频文件
    ↓
提取音频
    ↓
语音转文字
    ↓
文本清洗与时间戳分段
    ↓
保存转写结果
    ↓
调用可配置的 AI 模型进行总结和内容分析
    ↓
按配置转移或归档源文件，并记录完整转移历史
```

### 1.2 核心原则

1. **本地目录优先**：系统能够读取用户指定的本地输入目录，不依赖先上传到云端。
2. **结果可追溯**：每个文件、每次处理、每个输出结果和每次文件转移都可以查询。
3. **ASR 与 AI 解耦**：语音识别模型和 AI 内容分析模型均通过接口接入，可以独立替换。
4. **原始数据不覆盖**：原始媒体、原始 ASR 返回值、清洗后文本和 AI 结果分开保存。
5. **任务可恢复**：处理失败可以重试；应用重启后未完成任务能够恢复或明确标记。
6. **默认安全**：默认不删除源文件、不移动源文件，文件转移必须由用户显式配置。
7. **SQLite 持久化**：使用 SQLite 保存任务、文件、转写、分析、配置和文件转移记录。

### 1.3 产品定位

本产品是一个本地视频内容理解工具，而不是单纯的“视频转 TXT”脚本：

```text
视频/音频
    ↓
文案提取
    ↓
内容理解
    ↓
总结、观点、结构、风格
    ↓
改写和内容生产
```

### 1.4 目标用户

- 短视频创作者
- 自媒体运营人员
- 内容编辑
- 视频分析人员
- 短剧、小说和知识类内容创作者
- 需要批量整理本地视频素材的个人或小团队

### 1.5 非目标

第一阶段不要求：

- 公有云多租户部署
- 用户注册、登录和权限体系
- 在线视频 URL 解析
- 移动端原生应用
- 实时直播转写
- 自动发布到第三方平台

这些能力可以在后续版本扩展，但不能影响本地目录批处理主流程。

---

## 2. 使用场景

### 2.1 单目录批量处理

用户选择一个本地目录，系统扫描目录中的视频和音频文件，逐个创建处理任务，并将结果保存到结果目录和 SQLite。

### 2.2 增量处理

用户再次扫描同一目录时：

- 已成功处理且文件内容未变化的文件默认跳过。
- 新增文件自动创建任务。
- 文件内容发生变化时创建新的处理版本，保留历史结果。
- 上次失败的文件可以选择重试。

### 2.3 处理后转移或归档

用户可以配置处理完成后的文件动作：

```text
不处理源文件
复制到归档目录
移动到归档目录
复制到失败目录
移动到失败目录
```

每次复制或移动都必须记录源路径、目标路径、操作类型、校验值、状态和错误信息。

### 2.4 单文件处理

除目录扫描外，系统也应支持选择单个文件立即处理，便于调试和临时使用。

---

## 3. 总体处理流程

### 3.1 标准流程

```text
用户配置输入目录
    ↓
扫描文件
    ↓
按扩展名和文件特征筛选媒体文件
    ↓
计算文件指纹并去重
    ↓
创建文件记录和处理任务
    ↓
读取媒体元数据
    ↓
提取或准备音频
    ↓
ASR 语音识别
    ↓
生成带时间戳的原始分段
    ↓
文本清洗、断句、段落整理
    ↓
保存 TXT / JSON / SRT 等结果
    ↓
按策略调用 AI 分析
    ↓
保存 AI 分析结果
    ↓
执行文件复制、移动或归档
    ↓
记录文件转移结果
    ↓
任务完成
```

### 3.2 处理阶段

```text
DISCOVERED       已发现
QUEUED           排队中
PROBING          读取媒体信息
EXTRACTING       提取音频
TRANSCRIBING     语音识别
POST_PROCESSING  文本整理
SAVING           保存转写结果
ANALYZING        AI 分析
TRANSFERRING     文件转移
COMPLETED        已完成
COMPLETED_WITH_WARNINGS  已完成但有警告
FAILED           失败
CANCELED         已取消
```

### 3.3 状态规则

- `FAILED` 必须保存失败阶段、错误类型、用户可读错误信息和原始错误详情。
- 任务重试时创建新的任务执行记录，不能覆盖原失败记录。
- `COMPLETED` 只表示任务要求的全部阶段已成功完成。
- 如果用户关闭了 AI 分析，则转写成功并完成结果保存后即可进入 `COMPLETED`。
- 如果 AI 分析失败但转写成功，默认任务状态为 `COMPLETED_WITH_WARNINGS`，转写结果仍可查看，AI 分析可以单独重试。
- 文件转移失败时不得删除源文件，任务标记为 `COMPLETED_WITH_WARNINGS`，转移可以单独重试。

### 3.4 任务、重试和执行记录

系统将“业务任务”和“任务执行记录”统一落在 `processing_task` 表中：

- 首次处理创建一条 `processing_task`。
- 每次重试创建一条新的 `processing_task`，通过 `parent_task_id` 关联原任务。
- 原任务的失败状态、错误信息和事件记录永久保留，不允许覆盖。
- 页面按 `media_file_id` 或根任务展示处理历史，默认突出最新一次执行。
- 任务必须保存 `attempt_no`、`worker_id`、`heartbeat_at` 和 `cancel_requested`，用于恢复、取消和排查重复执行。

任务状态必须按照状态机变更，禁止接口直接把任意状态改成 `COMPLETED`：

```text
QUEUED
  ├──> CANCELED
  └──> RUNNING
          ├──> COMPLETED
          ├──> COMPLETED_WITH_WARNINGS
          ├──> FAILED
          └──> CANCELED
```

状态变化必须同时写入任务表和 `task_event`，两者在同一数据库事务中提交。

---

## 4. 输入目录与文件管理

### 4.1 输入目录配置

用户可以配置：

- 输入目录
- 是否递归扫描子目录
- 是否监听目录变化
- 扫描间隔
- 文件稳定时间
- 允许的文件扩展名
- 排除目录和排除文件模式
- 单次最大处理数量

### 4.2 文件稳定判断

为了避免扫描到仍在复制中的视频，系统发现文件后必须满足以下条件才允许进入处理队列：

- 文件大小在连续两次检查中保持不变。
- 文件最后修改时间距离当前时间超过配置的稳定等待时间。
- 文件能够被 FFprobe 或 FFmpeg 正常读取媒体信息。

### 4.3 支持的格式

视频：

```text
mp4、mov、mkv、avi、webm、m4v、flv、ts
```

音频：

```text
mp3、wav、m4a、flac、aac、ogg、opus、weba、wma
```

扩展名不能作为唯一判断依据；必要时应使用 FFprobe 或 FFmpeg 读取媒体流信息。

### 4.4 文件指纹与去重

每个媒体文件至少记录：

- 规范化绝对路径
- 文件名
- 文件大小
- 最后修改时间
- SHA-256 文件哈希，或可配置的快速指纹
- 文件类型

默认去重规则：

```text
同一规范化路径 + 文件大小 + 修改时间未变化
    → 视为同一个文件版本

路径相同但文件指纹变化
    → 创建新的文件版本和处理任务

路径不同但文件哈希相同
    → 标记为重复文件，可由用户选择是否处理
```

---

## 5. 文件转移与归档记录

### 5.1 转移策略

系统必须支持按任务结果配置文件动作：

| 策略 | 成功后动作 | 失败后动作 |
|---|---|---|
| 保留 | 不处理源文件 | 不处理源文件 |
| 复制归档 | 复制到成功目录 | 不处理源文件 |
| 移动归档 | 移动到成功目录 | 不处理源文件 |
| 分类归档 | 成功和失败分别复制或移动到对应目录 | 按失败目录策略执行 |

默认策略为“保留源文件”。

### 5.2 目标路径规则

目标目录支持模板变量：

```text
{date}         处理日期，例如 2026-09-09
{year}         年份
{month}        月份
{source_dir}   输入目录名称
{status}       任务状态
{stem}         不含扩展名的文件名
{filename}     原始文件名
```

示例：

```text
archive/{date}/{source_dir}/{stem}/{filename}
```

目标文件已存在时必须有明确策略：

- 跳过
- 覆盖
- 自动追加序号
- 比较哈希后跳过相同文件

默认使用“比较哈希后跳过相同文件，否则自动追加序号”，不允许静默覆盖。

### 5.3 转移执行要求

1. 转移前检查源文件是否存在。
2. 复制完成后校验目标文件大小和哈希。
3. 移动操作优先使用同一文件系统内的原子重命名；跨磁盘时退化为复制、校验、删除源文件。
4. 只有目标文件校验成功后，才允许删除移动操作中的源文件。
5. 任意步骤失败都保留源文件，并记录失败原因。
6. 转移操作支持单独重试，不要求重新执行 ASR。

### 5.4 转移记录内容

每次复制或移动都需要写入记录：

- 转移记录 ID
- 关联任务 ID
- 源文件路径
- 目标文件路径
- 操作类型：COPY / MOVE
- 开始时间
- 完成时间
- 源文件大小
- 目标文件大小
- 源文件哈希
- 目标文件哈希
- 状态：PENDING / RUNNING / SUCCESS / FAILED / SKIPPED
- 错误信息
- 重试次数

---

## 6. 音频处理

### 6.1 FFmpeg

视频输入默认使用应用内置的 FFmpeg 提取音频，统一转换为：

系统不能要求用户单独安装 FFmpeg，也不能把系统 `PATH` 中的 FFmpeg 作为生产运行前提。发布包必须携带当前目标平台的 `ffmpeg` 和 `ffprobe`。

建议发布目录：

```text
runtime/
└── ffmpeg/
    ├── windows-x64/
    │   ├── ffmpeg.exe
    │   └── ffprobe.exe
    ├── linux-x64/
    │   ├── ffmpeg
    │   └── ffprobe
    └── macos-arm64/
        ├── ffmpeg
        └── ffprobe
```

媒体处理服务必须通过统一的 `MediaToolchain` 获取工具路径：

```python
class MediaToolchain:
    def ffmpeg_path(self) -> str:
        ...

    def ffprobe_path(self) -> str:
        ...

    def check(self) -> None:
        ...
```

要求：

- 应用启动时检查内置工具是否存在且可执行。
- 开发环境允许通过配置显式指定外部工具路径，但生产默认使用内置版本。
- 记录 FFmpeg 版本和许可证信息，遵守所选构建包的分发许可证。
- FFmpeg 二进制不提交到源代码仓库，由发布构建流程或安装包携带。

```text
格式：WAV
编码：PCM S16LE
采样率：16000 Hz
声道：Mono
```

核心参数：

```text
-vn
-acodec pcm_s16le
-ar 16000
-ac 1
```

音频文件可以直接交给 ASR；用户也可以通过配置强制转换为统一 WAV。

### 6.2 媒体信息

处理前读取并保存：

- 视频宽度和高度
- 视频时长
- 音频时长
- 文件格式
- 视频编码
- 音频编码
- 采样率
- 声道数
- 是否包含音频流

### 6.3 音频提取失败

失败时必须：

- 任务进入失败或带警告状态。
- 保存 FFmpeg 退出码和压缩后的错误详情。
- 提示可能原因：文件损坏、没有音轨、格式不支持、权限不足、内置媒体工具缺失或执行失败。
- 不删除、不移动源文件。

---

## 7. 语音识别 ASR

### 7.1 技术关系

本项目不是在 `QwenAudio/SenseVoice` 和 FunASR 之间二选一：

```text
QwenAudio/SenseVoice
    = SenseVoice 官方代码、示例和模型说明

SenseVoiceSmall
    = 实际使用的语音识别模型

FunASR
    = Python 推理框架、模型加载、VAD 和长音频处理框架
```

正式后端采用：

```text
FunASR + iic/SenseVoiceSmall + fsmn-vad
```

官方参考：

- [QwenAudio/SenseVoice](https://github.com/QwenAudio/SenseVoice)
- [FunASR](https://github.com/modelscope/FunASR)
- [SenseVoice 中文说明](https://github.com/QwenAudio/SenseVoice/blob/main/README_zh.md)

### 7.2 默认实现

第一阶段默认使用：

```text
FunASR + SenseVoiceSmall
VAD：fsmn-vad
```

默认模型：

```text
iic/SenseVoiceSmall
```

当前 Python 脚本 `video_to_text.py` 仅作为 ASR 流程参考和独立 CLI 工具。后端必须参考该脚本重新编写独立的 ASR Provider，不得导入或调用 `video_to_text.py`。

### 7.3 ASR 配置

以下参数不能写死在业务流程中，应通过配置或任务参数传入：

- ASR Provider
- 模型名称或本地模型目录
- 推理设备：auto、cpu、cuda:0 等
- 语言
- 是否启用 ITN
- batch size
- VAD 单段最大时长
- VAD 合并目标长度
- 是否强制音频转换

当前开发电脑为 R5 5600、16 GB 内存、GTX 1060 3 GB，MVP 默认配置为：

```yaml
asr:
  provider: sensevoice
  model: iic/SenseVoiceSmall
  device: cpu
  batch_size_s: 30
  max_single_segment_time_ms: 30000

worker:
  max_concurrency: 1
```

3 GB 显存不作为默认 CUDA 推理设备。升级显卡后，必须重新验证 PyTorch、FunASR 和模型组合，再开启 GPU。

### 7.4 支持语言

第一阶段支持：

```text
自动检测、中文、英文、粤语、日语、韩语
```

识别结果中必须记录：

- 用户选择的语言
- 模型推断语言，如模型能够提供
- 识别置信度，如模型能够提供

### 7.5 ASR 结果

ASR 返回结构化结果，不允许只返回一段纯文本：

```json
{
  "language": "zh",
  "text": "完整识别文本",
  "segments": [
    {
      "sequence": 1,
      "start": 0.5,
      "end": 5.2,
      "text": "大家好，今天我们来聊一个问题。",
      "speaker": null,
      "confidence": null
    }
  ]
}
```

必须至少保存：

- 原始返回 JSON
- 原始完整文本
- 原始分段
- 分段开始时间和结束时间
- 分段顺序

---

## 8. 文本后处理

### 8.1 数据分层

原始 ASR 文本和清洗后文本必须分开保存：

```text
raw_transcript
    ↓
clean_transcript
    ↓
ai_input_text
```

### 8.2 清洗内容

文本处理模块可以包含：

- `rich_transcription_postprocess`
- 多余空格清理
- 重复标点清理
- 明显的断句修复
- 语气词处理
- 短分段合并
- 段落划分
- 中英文标点统一

未经用户确认，不得擅自大幅改写原始内容。

### 8.3 结果版本

清洗规则发生变化时，应生成新的文本版本，而不是覆盖历史版本。每个版本需要记录：

- 处理规则版本
- 创建时间
- 输入转写版本
- 清洗后的完整文本
- 清洗后的分段

---

## 9. AI 内容分析

### 9.1 设计要求

AI 内容分析不是写死在业务代码中的单一模型调用，而是一个可配置、可替换的 Provider 能力。

需要支持：

```text
OpenAI
OpenAI Compatible API
DeepSeek
Claude
Gemini
本地模型
自定义 HTTP API
```

第一阶段至少实现：

- OpenAI Compatible API
- 本地模型或自定义 Provider 的扩展接口

### 9.2 Provider 配置

每个 Provider 支持独立配置：

- Provider 名称
- API 类型
- Base URL
- API Key
- 模型名称
- Temperature
- Max Tokens
- 请求超时
- 最大重试次数
- 是否启用

API Key 默认只保存配置引用或加密后的值，日志中不得输出明文 Key。

### 9.3 Prompt 配置

每项 AI 能力使用独立 Prompt 模板：

```text
summary.prompt
outline.prompt
key_points.prompt
golden_sentences.prompt
structure.prompt
style.prompt
rewrite.prompt
```

Prompt 不得硬编码在多个业务函数中。每次 AI 分析都要记录：

- Prompt 模板名称
- Prompt 版本
- Provider
- 模型名称
- 请求参数
- 输入文本版本
- 输出内容
- 创建时间
- 调用耗时
- Token 使用量，如 Provider 能够提供

### 9.4 第一阶段 AI 能力

第一阶段实现以下分析：

1. 一句话总结
2. 详细总结
3. 核心观点
4. 内容大纲
5. 金句提取

### 9.5 后续 AI 能力

后续增加：

- 内容结构分析
- 表达风格分析
- 语言特点分析
- 情绪分析
- 短视频文案改写
- 标题生成
- 开头钩子生成
- 多平台风格改写

### 9.6 长文本处理

长视频不能无条件把完整文案一次发送给 LLM。采用 Map-Reduce 方式：

```text
完整文案
    ↓
按字符数或 Token 数分块
    ↓
分别总结各分块
    ↓
汇总分块结果
    ↓
生成最终分析
```

分块参数应可配置：

- 最大输入 Token
- 分块长度
- 分块重叠长度
- 汇总模型
- 单次并发数

---

## 10. SQLite 数据库设计

### 10.1 数据库要求

- 默认数据库文件：`data/video_content.db`
- 使用 SQLite 保存业务数据。
- 数据库连接必须启用外键约束。
- 时间统一保存为 ISO 8601 格式，建议使用 UTC 或明确的本地时区。
- 所有任务状态变更和关键文件操作必须在数据库中留痕。
- 数据库初始化必须支持版本迁移。
- 不将视频二进制内容直接存入 SQLite，数据库只保存路径、元数据和结果文本。

### 10.2 `scan_source` 扫描源表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| name | TEXT | 扫描源名称 |
| input_dir | TEXT | 输入目录绝对路径 |
| recursive | INTEGER | 是否递归扫描 |
| watch_enabled | INTEGER | 是否监听变化 |
| scan_interval_seconds | INTEGER | 扫描间隔 |
| include_extensions | TEXT | 允许扩展名 JSON |
| exclude_patterns | TEXT | 排除规则 JSON |
| enabled | INTEGER | 是否启用 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 10.3 `media_file` 媒体文件表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| scan_source_id | INTEGER | 扫描源 ID |
| path | TEXT | 当前文件绝对路径 |
| original_path | TEXT | 首次发现时的路径 |
| file_name | TEXT | 文件名 |
| extension | TEXT | 扩展名 |
| media_type | TEXT | VIDEO / AUDIO |
| file_size | INTEGER | 文件大小 |
| modified_at | TEXT | 文件修改时间 |
| content_hash | TEXT | 文件哈希或快速指纹 |
| duration_seconds | REAL | 时长 |
| status | TEXT | ACTIVE / MISSING / DUPLICATE |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

约束和索引：

- `path` 建立索引。
- `content_hash` 建立索引。
- 同一路径同一文件指纹只能对应一个有效文件版本。

### 10.4 `processing_task` 处理任务表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| media_file_id | INTEGER | 媒体文件 ID |
| parent_task_id | INTEGER | 重试任务的原任务 ID |
| status | TEXT | 处理状态 |
| current_stage | TEXT | 当前阶段 |
| progress | INTEGER | 0-100 |
| retry_count | INTEGER | 重试次数 |
| attempt_no | INTEGER | 当前媒体文件的执行序号，从 1 开始 |
| requested_ai | INTEGER | 是否要求 AI 分析 |
| transfer_policy | TEXT | 文件转移策略 |
| worker_id | TEXT | 当前 Worker 标识，可为空 |
| heartbeat_at | TEXT | 最近心跳时间，可为空 |
| cancel_requested | INTEGER | 是否请求取消 |
| root_task_id | INTEGER | 同一重试链的根任务 ID |
| error_code | TEXT | 错误编码 |
| error_message | TEXT | 用户可读错误 |
| error_detail | TEXT | 原始错误详情 |
| started_at | TEXT | 开始时间 |
| finished_at | TEXT | 完成时间 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 10.5 `task_event` 任务事件表

用于记录可追踪的阶段变化：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| task_id | INTEGER | 任务 ID |
| stage | TEXT | 事件阶段 |
| level | TEXT | INFO / WARNING / ERROR |
| code | TEXT | 机器可识别的事件编码，可为空 |
| message | TEXT | 用户可读消息 |
| detail | TEXT | 详细信息 JSON |
| progress | INTEGER | 事件发生时的任务进度 |
| duration_ms | INTEGER | 阶段耗时，可为空 |
| source | TEXT | WEB / WORKER / SYSTEM |
| created_at | TEXT | 创建时间 |

### 10.6 `transcript` 转写结果表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| task_id | INTEGER | 任务 ID |
| version | INTEGER | 转写版本 |
| asr_provider | TEXT | ASR Provider |
| model_name | TEXT | 模型名称 |
| requested_language | TEXT | 请求语言 |
| detected_language | TEXT | 检测语言 |
| raw_text | TEXT | 原始文本 |
| clean_text | TEXT | 清洗后文本 |
| raw_result_json | TEXT | 原始 ASR JSON |
| clean_rule_version | TEXT | 清洗规则版本 |
| created_at | TEXT | 创建时间 |

约束：

- 同一个任务可以有多个结果版本。
- 默认将最新成功版本标记为当前版本，历史版本保留。

### 10.7 `transcript_segment` 转写分段表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| transcript_id | INTEGER | 转写结果 ID |
| sequence | INTEGER | 分段顺序 |
| start_time | REAL | 开始时间，秒 |
| end_time | REAL | 结束时间，秒 |
| raw_text | TEXT | 原始分段文本 |
| clean_text | TEXT | 清洗后分段文本 |
| speaker | TEXT | 说话人，可为空 |
| confidence | REAL | 置信度，可为空 |

### 10.8 `ai_provider` AI Provider 配置表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| name | TEXT | Provider 名称 |
| provider_type | TEXT | OPENAI_COMPATIBLE / LOCAL / CUSTOM |
| base_url | TEXT | API 地址 |
| api_key_ref | TEXT | Key 引用或加密值 |
| default_model | TEXT | 默认模型 |
| temperature | REAL | 默认温度 |
| max_tokens | INTEGER | 默认最大输出 Token |
| timeout_seconds | INTEGER | 请求超时 |
| max_retries | INTEGER | 最大重试次数 |
| enabled | INTEGER | 是否启用 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 10.9 `prompt_template` Prompt 模板表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| key | TEXT | 能力标识，如 summary |
| version | INTEGER | 模板版本 |
| name | TEXT | 模板名称 |
| content | TEXT | Prompt 内容 |
| variables | TEXT | 变量定义 JSON |
| enabled | INTEGER | 是否启用 |
| created_at | TEXT | 创建时间 |

### 10.10 `ai_analysis` AI 分析结果表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| task_id | INTEGER | 任务 ID |
| transcript_id | INTEGER | 使用的转写版本 |
| provider_id | INTEGER | 使用的 Provider |
| prompt_template_id | INTEGER | 使用的 Prompt |
| analysis_type | TEXT | SUMMARY / OUTLINE / KEY_POINTS 等 |
| model_name | TEXT | 实际模型 |
| input_text_hash | TEXT | 输入文本哈希 |
| request_json | TEXT | 请求参数 |
| content | TEXT | AI 输出内容 |
| raw_response_json | TEXT | 原始响应 |
| token_usage_json | TEXT | Token 用量 |
| status | TEXT | RUNNING / SUCCESS / FAILED |
| error_message | TEXT | 错误信息 |
| duration_ms | INTEGER | 调用耗时 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 10.11 `file_transfer` 文件转移表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| task_id | INTEGER | 任务 ID |
| operation | TEXT | COPY / MOVE |
| source_path | TEXT | 源路径 |
| target_path | TEXT | 目标路径 |
| source_size | INTEGER | 源文件大小 |
| target_size | INTEGER | 目标文件大小 |
| source_hash | TEXT | 源文件哈希 |
| target_hash | TEXT | 目标文件哈希 |
| status | TEXT | PENDING / RUNNING / SUCCESS / FAILED / SKIPPED |
| retry_count | INTEGER | 重试次数 |
| error_message | TEXT | 错误信息 |
| started_at | TEXT | 开始时间 |
| finished_at | TEXT | 完成时间 |
| created_at | TEXT | 创建时间 |

### 10.12 `export_record` 导出记录表

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER | 主键 |
| task_id | INTEGER | 任务 ID |
| export_type | TEXT | TXT / JSON / SRT / MD |
| file_path | TEXT | 导出文件路径 |
| content_version | TEXT | 内容版本 |
| created_at | TEXT | 创建时间 |

### 10.13 数据库约束和索引

必须建立以下约束或索引：

- 所有外键启用 `ON DELETE` 策略，删除任务前先明确处理结果、事件和导出记录。
- `media_file(path, file_size, modified_at)` 建立组合索引，用于增量扫描。
- `processing_task(status, created_at)` 建立索引，用于 Worker 领取任务。
- `processing_task(media_file_id, created_at)` 建立索引，用于展示重试历史。
- `task_event(task_id, created_at)` 建立索引，用于时间线查询。
- `transcript(task_id, version)` 建立唯一约束。
- `ai_analysis(task_id, analysis_type, transcript_id, prompt_template_id, provider_id)` 建立查询索引。
- `file_transfer(task_id, created_at)` 建立索引。

数据库迁移必须可重复执行，并在启动日志中打印当前 schema 版本。

---

## 11. 数据保留与文件组织

推荐目录结构：

```text
data/
├── video_content.db
├── cache/
│   └── audio/
├── results/
│   └── {task_id}/
│       ├── transcript.txt
│       ├── transcript.json
│       ├── transcript.srt
│       └── analysis/
├── logs/
└── archive/
```

要求：

- 临时音频放在缓存目录或临时目录中。
- 任务完成后根据清理策略删除临时音频。
- 原始媒体文件默认不移动、不删除。
- 结果文件路径写入数据库，结果正文也写入数据库，避免单独文件丢失后无法查询。
- 大型原始响应可同时保存文件和数据库摘要，但数据库必须保留可定位信息。

---

## 12. 后端架构

本项目采用本地部署的模块化单体架构，后端统一使用 Python：

```text
浏览器操作界面
        │
        ↓
FastAPI 页面和 API 服务
        │
        ├── SQLite：任务、结果、配置、事件和转移记录
        ├── 本地文件系统：视频、结果和归档文件
        └── 独立 Python Worker：扫描、转写、AI 分析、文件转移
                         │
                         ├── 内置 FFmpeg / FFprobe
                         ├── 独立 SenseVoice ASR Provider
                         └── 可替换的 LLM Provider
```

默认访问地址：

```text
http://127.0.0.1:8000
```

### 12.1 进程职责

Web 进程负责：

- 提供操作界面和 REST API。
- 保存扫描源、任务和系统配置。
- 查询 SQLite 并返回任务进度。
- 接收开始、取消、重试和导出等操作。

Worker 进程负责：

- 扫描本地目录并创建任务。
- 领取并执行排队任务。
- 调用内置 FFmpeg / FFprobe、独立 SenseVoice Provider 和 LLM Provider。
- 保存阶段状态、事件、结果和错误。
- 执行文件复制、移动和哈希校验。

长耗时处理不能占用同步 HTTP 请求。MVP 使用一个独立 Worker 进程和 SQLite 任务表，不引入 Redis、Celery 或其他外部队列。

### 12.2 任务处理流程

```text
浏览器操作
    │
    ↓
FastAPI
    │
写入 SQLite
    ↓
Worker 原子领取任务
    ↓
读取媒体信息
    ↓
FFmpeg 提取音频
    ↓
SenseVoice 识别
    ↓
文本清洗和结果保存
    ↓
可选 AI 分析
    ↓
可选文件转移
```

前端通过 HTMX 定时请求任务进度接口刷新状态。后续需要更强实时性时再增加 SSE，不把 WebSocket 作为 MVP 前置依赖。

### 12.3 推荐模块

```text
app/
├── main.py
├── config.py
├── api/
│   ├── scan_sources.py
│   ├── tasks.py
│   ├── transcripts.py
│   ├── analyses.py
│   ├── transfers.py
│   └── exports.py
├── web/
│   └── views.py
├── templates/
│   ├── dashboard.html
│   ├── scan_sources.html
│   ├── tasks.html
│   ├── task_detail.html
│   └── settings.html
├── static/
│   ├── css/
│   └── js/
├── domain/
│   ├── enums.py
│   ├── task_states.py
│   └── schemas.py
├── db/
│   ├── database.py
│   ├── models.py
│   └── migrations/
├── repositories/
│   ├── media_file.py
│   ├── processing_task.py
│   ├── transcript.py
│   ├── analysis.py
│   └── file_transfer.py
├── services/
│   ├── scanner.py
│   ├── media_probe.py
│   ├── media_toolchain.py
│   ├── audio_extractor.py
│   ├── pipeline.py
│   ├── text_processor.py
│   ├── file_transfer.py
│   ├── exporter.py
│   ├── asr/
│   │   ├── base.py
│   │   └── sensevoice_provider.py
│   └── llm/
│       ├── base.py
│       ├── openai_compatible.py
│       └── prompt_manager.py
├── worker/
│   ├── worker.py
│   ├── task_runner.py
│   └── scheduler.py
├── runtime/
│   └── ffmpeg/                 # 发布包内置 FFmpeg/FFprobe
└── start.py
```

完整目录和进程说明见《系统架构设计.md》。

### 12.4 ASR 接口

```python
class ASRProvider:
    def transcribe(
        self,
        audio_path: str,
        language: str,
        options: dict,
    ) -> dict:
        ...
```

返回值必须包含完整文本和分段信息。后续替换 SenseVoice、Whisper、WhisperX 或其他 ASR 时，不应修改任务编排逻辑。

### 12.5 LLM 接口

```python
class LLMProvider:
    def generate(
        self,
        prompt: str,
        options: dict,
    ) -> dict:
        ...
```

业务层只依赖统一接口，不依赖具体厂商 SDK。Provider 负责：

- 请求构造
- 鉴权
- 超时
- 重试
- 响应解析
- Token 用量提取
- 错误分类

---

## 13. 前端功能需求

### 13.1 操作界面技术方案

MVP 使用 FastAPI 提供页面，Jinja2 渲染 HTML，HTMX 完成局部刷新，少量原生 JavaScript 负责视频播放、时间戳联动、复制和下载。

操作界面必须运行在本机浏览器中，但视频和音频由本机 Python 后端直接读取。用户通过界面填写本地目录绝对路径，不把本地视频上传到云端。

页面统一访问：

```text
http://127.0.0.1:8000
```

### 13.2 扫描源管理

支持：

- 添加本地输入目录
- 修改扫描目录
- 开关递归扫描
- 开关自动监听
- 配置文件扩展名
- 配置排除规则
- 手动立即扫描
- 查看最近扫描时间和扫描结果

### 13.3 任务列表

显示：

- 文件名称
- 文件路径
- 文件大小
- 视频时长
- 当前阶段
- 进度
- AI 分析状态
- 文件转移状态
- 创建时间
- 完成时间

操作：

- 查看详情
- 开始处理
- 暂停或取消
- 重试
- 仅重试 AI 分析
- 仅重试文件转移
- 删除任务记录
- 打开源文件所在目录
- 打开结果目录

### 13.4 任务详情

展示：

- 媒体基本信息
- 任务阶段时间线
- 当前状态和错误信息
- 原始转写
- 清洗后文案
- 带时间戳分段
- AI 分析结果
- 文件转移记录
- 处理事件日志

### 13.5 文案查看

支持：

- 按分段查看文本
- 时间戳展示
- 视频播放与文案分段联动
- 点击文本跳转到对应时间
- 复制全文
- 编辑清洗后文案
- 导出 TXT、Markdown、SRT、JSON

用户编辑后的文本必须作为新的人工修订版本保存，不能覆盖原始 ASR 文本。

### 13.6 AI 分析

使用 Tab 或能力列表展示：

```text
总结
大纲
核心观点
金句
结构
风格
改写
```

用户可以：

- 选择 Provider 和模型
- 选择 Prompt 模板
- 修改自定义要求
- 重新生成
- 停止生成
- 查看调用参数和耗时
- 复制结果
- 将结果导出

### 13.7 设置

设置页面至少包括：

- SQLite 数据库路径
- 默认输入目录
- 默认结果目录
- 默认归档目录
- 扫描规则
- 文件转移策略
- 默认 ASR 配置
- AI Provider 配置
- Prompt 模板管理
- 日志级别
- 缓存清理策略

---

## 14. API 需求

后端使用 FastAPI 提供 REST API。MVP 使用 HTMX 定时轮询刷新任务状态，后续可增加 SSE。API 不执行长耗时任务，只负责创建任务、查询状态和返回结果。

### 14.1 扫描源

```text
GET    /api/scan-sources
POST   /api/scan-sources
PUT    /api/scan-sources/{id}
DELETE /api/scan-sources/{id}
POST   /api/scan-sources/{id}/scan
```

扫描接口只负责扫描并写入任务，不同步等待视频处理完成。

### 14.2 任务

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{id}
POST   /api/tasks/{id}/retry
POST   /api/tasks/{id}/cancel
DELETE /api/tasks/{id}
```

创建任务后立即返回任务 ID：

```json
{
  "taskId": 123,
  "status": "QUEUED"
}
```

### 14.3 任务状态

```text
GET /api/tasks/{id}/events
GET /api/tasks/{id}/progress
GET /api/tasks/{id}/stream
```

MVP 页面使用 `/progress` 和 `/events` 轮询；`/stream` 作为后续 SSE 扩展接口预留。

示例：

```json
{
  "taskId": 123,
  "status": "TRANSCRIBING",
  "stage": "语音识别",
  "progress": 68,
  "message": "正在识别音频，请稍候",
  "updatedAt": "2026-09-09T11:28:37+08:00"
}
```

### 14.4 转写和导出

```text
GET  /api/tasks/{id}/transcript
GET  /api/tasks/{id}/segments
POST /api/tasks/{id}/export
GET  /api/exports/{id}/download
```

### 14.5 AI 分析

```text
GET  /api/tasks/{id}/analyses
POST /api/tasks/{id}/analyses
POST /api/analyses/{id}/retry
DELETE /api/analyses/{id}
```

### 14.6 文件转移

```text
GET  /api/tasks/{id}/transfers
POST /api/transfers/{id}/retry
```

### 14.7 系统检查

```text
GET  /api/health
GET  /api/system/info
POST /api/system/check-media-tools
POST /api/system/check-asr
POST /api/system/check-ai/{provider_id}
```

检查接口返回结构化结果：

```json
{
  "name": "ffmpeg",
  "status": "OK",
  "message": "内置媒体工具可用",
  "version": "..."
}
```

`/api/health` 只表示 Web 服务和 SQLite 可用；FFmpeg、ASR 模型和 AI Provider 作为独立能力返回检查结果，避免可选组件故障导致整个操作界面不可用。

---

## 15. 日志、错误和可观测性

### 15.1 控制台日志

普通用户看到的日志应使用简洁的人话，不直接显示 ASR 框架内部的 tqdm、`rtf_avg`、模型 cache 或完整堆栈。控制台采用“阶段开始 + 阶段完成/失败”的低噪声输出：

```text
11:28:37 | INFO    | 任务 #123 | 开始处理：example.mp4
11:28:38 | INFO    | 任务 #123 | 读取媒体信息完成：时长 05:32 | 含音频
11:28:39 | INFO    | 任务 #123 | 正在提取音频
11:28:42 | INFO    | 任务 #123 | 正在识别音频，请稍候
11:29:18 | INFO    | 任务 #123 | 识别完成：耗时 36.4 秒 | 12 段 | 1,256 字
11:29:18 | INFO    | 任务 #123 | 已保存转写结果：TXT、JSON、SRT
11:29:18 | SUCCESS | 任务 #123 | 处理完成
```

要求：

- 一行只表达一个事件，消息使用人话和固定阶段名称。
- 不输出动态 tqdm 进度条，不输出 `rtf_avg`、`cache`、模型内部批处理信息。
- 同一阶段默认最多输出开始和结束两条日志；长阶段不刷屏。
- 文件名显示相对名，完整路径只在 DEBUG 日志或详情页显示。
- 任务失败显示“发生了什么 + 如何处理”，技术堆栈写入日志文件。
- 日志级别至少支持 `INFO`、`SUCCESS`、`WARNING`、`ERROR`、`DEBUG`。

内部调试信息写入按天滚动的日志文件，但不能影响正常控制台输出。控制台日志和 `task_event` 必须由同一个 `AppLogger` 适配器生成，避免页面和终端出现两套说法。

### 15.2 错误分类

错误至少分为：

```text
INPUT_NOT_FOUND
INPUT_NOT_STABLE
UNSUPPORTED_MEDIA
NO_AUDIO_STREAM
FFMPEG_NOT_FOUND
FFMPEG_FAILED
ASR_DEPENDENCY_MISSING
ASR_MODEL_LOAD_FAILED
ASR_INFERENCE_FAILED
LLM_CONFIG_INVALID
LLM_AUTH_FAILED
LLM_TIMEOUT
LLM_RATE_LIMITED
LLM_TOKEN_LIMIT
FILE_TRANSFER_FAILED
OUTPUT_WRITE_FAILED
```

错误信息分为：

- 用户可读信息
- 技术错误详情
- 建议处理方式

### 15.3 日志要求

- 日志包含任务 ID 和文件 ID。
- API Key、Authorization Header 和敏感路径信息不得明文输出。
- 日志级别支持 INFO、WARNING、ERROR、DEBUG。
- 单个任务的关键事件写入 `task_event`。
- 进程重启后能够通过数据库恢复任务状态。
- 每条日志尽量包含 `task_id`、`media_file_id`、`stage`、`elapsed_ms` 等结构化字段。
- 控制台默认使用 UTF-8，并兼容 Windows PowerShell、CMD 和重定向到文件。
- 外部命令的完整参数必须脱敏；API Key、Authorization、Cookie 和本地密钥不得落盘。

---

## 16. 可靠性与安全要求

### 16.1 可靠性

- 同一任务不能被多个 Worker 重复执行，除非显式允许并发。
- Worker 获取任务时使用数据库锁或状态条件更新。
- 应用重启后，`RUNNING` 状态任务应根据心跳超时规则恢复为可重试状态。
- Worker 在处理长任务时每隔固定时间更新 `heartbeat_at`；超过 `stale_task_timeout_seconds` 未更新的任务才允许恢复。
- 取消操作采用协作式取消：任务在阶段边界和外部命令结束后检查取消标记；不得强制删除正在写入的结果文件。
- 所有阶段应支持幂等执行。
- 已存在且校验一致的输出文件可以复用，避免重复生成。
- 长任务不能因为前端页面关闭而中断。

### 16.2 安全

- 默认只允许访问用户配置的目录。
- 所有路径必须规范化并校验，防止通过 `..` 越界访问。
- 归档目标目录不能通过模板逃逸到未授权目录。
- API Key 不出现在控制台、任务事件和普通错误中。
- 用户导出的内容不能执行脚本。
- 本地 API 默认只监听 `127.0.0.1`，如需局域网访问必须显式开启。

### 16.3 资源控制

- 限制单个文件大小和最大视频时长，可配置。
- 限制同时运行的 ASR 任务数。
- 限制同时运行的 AI 请求数。
- 控制临时音频和结果缓存的磁盘占用。
- GPU 显存不足时提供明确错误并允许切换 CPU。
- 默认只允许一个 ASR 任务同时运行；在 16 GB 内存和 GTX 1060 3 GB 的基线机器上不得默认启用 CUDA 并发。
- 模型首次下载、缓存目录和结果目录必须提供磁盘空间检查；空间不足时在开始识别前失败，而不是运行到中途才失败。

---

## 17. MVP 范围

### 17.1 必须实现

1. 配置一个或多个本地输入目录。
2. 扫描视频和音频文件。
3. 支持递归扫描和基本扩展名过滤。
4. 识别文件稳定性，避免处理未复制完成的文件。
5. 使用 SQLite 保存文件和任务记录。
6. 使用应用内置 FFmpeg 从视频提取 16 kHz 单声道 WAV。
7. 使用 FunASR / SenseVoiceSmall 完成语音识别。
8. 使用 FSMN-VAD 进行语音切分。
9. 保存原始 ASR JSON。
10. 保存原始文本、清洗后文本和时间戳分段。
11. 支持 TXT、JSON、SRT 导出。
12. 支持任务状态、进度、错误和重试。
13. 支持配置是否调用 AI 分析。
14. 支持一个 OpenAI Compatible AI Provider。
15. 支持一句话总结、详细总结、核心观点、大纲和金句。
16. 支持独立 Prompt 模板配置。
17. 支持保留源文件、复制归档和移动归档。
18. 保存完整文件转移记录。
19. 支持单独重试 AI 分析和文件转移。
20. 控制台不显示难以理解的 ASR 内部进度条和诊断输出。

### 17.2 MVP 暂不实现

- 多用户权限
- 云端对象存储
- 视频 URL 下载
- 实时直播转写
- 自动发布
- 复杂团队协作
- 复杂可视化报表

---

## 18. 开发阶段

### Phase 1：本地文件和任务基础

```text
SQLite
    ↓
扫描源管理
    ↓
文件发现、指纹和去重
    ↓
任务状态和事件记录
```

### Phase 2：媒体处理和 ASR

```text
内置 FFprobe / FFmpeg
    ↓
音频提取
    ↓
SenseVoice
    ↓
原始分段和文本结果
```

### Phase 3：结果和导出

```text
文本清洗
    ↓
TXT / JSON / SRT
    ↓
结果查看和视频时间戳联动
```

### Phase 4：AI 分析

```text
Provider 配置
    ↓
Prompt 模板
    ↓
总结 / 大纲 / 观点 / 金句
    ↓
长文本分块和汇总
```

### Phase 5：文件归档

```text
复制 / 移动策略
    ↓
目标路径模板
    ↓
哈希校验
    ↓
文件转移历史和独立重试
```

### Phase 6：扩展能力

```text
更多 ASR
更多 LLM Provider
结构和风格分析
AI 改写
批量导出
目录实时监听
```

---

## 19. MVP 验收标准

准备一个包含以下文件的本地目录：

```text
input/
├── example.mp4
├── example2.mp4
├── audio.mp3
└── subdir/
    └── nested.mp4
```

系统应满足：

1. 能配置并扫描 `input/` 目录。
2. 开启递归后能发现 `subdir/nested.mp4`。
3. 扫描过程中不会处理仍在写入的文件。
4. 每个媒体文件在 SQLite 中有唯一记录。
5. 相同文件重复扫描不会重复创建成功任务。
6. 文件内容变化后能够生成新的文件版本或处理任务。
7. 视频能够通过应用内置 FFmpeg 提取音频。
8. 没有音轨或文件损坏时，任务失败原因可查询。
9. SenseVoice 能生成完整文本和时间戳分段。
10. 原始 ASR JSON、原始文本和清洗后文本均被保留。
11. TXT、JSON、SRT 导出内容正确。
12. AI Provider 可以在配置页面修改 Base URL、Key 和模型名称。
13. 不修改业务代码即可切换兼容 OpenAI 协议的模型。
14. AI 总结使用独立 Prompt 模板，并记录 Provider、模型和 Prompt 版本。
15. 长文案超过单次输入限制时会自动分块处理。
16. 关闭 AI 分析时，转写任务仍能独立完成。
17. AI 调用失败时，转写结果不丢失，且 AI 可以单独重试。
18. 配置移动归档后，目标文件校验成功才删除源文件。
19. 文件转移失败时源文件保留，并能查看失败记录和重新执行。
20. 应用重启后，未完成任务不会无记录丢失。
21. 控制台显示清晰的阶段日志，不显示 `rtf_avg`、tqdm 进度条等内部实现细节。

---

## 20. 结论

平台最终形成以下稳定链路：

```text
本地目录
    ↓
视频/音频文件
    ↓
FFmpeg 音频处理
    ↓
可替换的 ASR Provider
    ↓
原始转写 + 时间戳分段
    ↓
文本清洗和版本管理
    ↓
可替换的 LLM Provider
    ↓
总结、观点、大纲、金句和改写
    ↓
TXT / JSON / SRT / Markdown
    ↓
可选文件归档或移动
    ↓
SQLite 中完整保存任务、结果、事件和转移记录
```

最重要的边界是：

```text
ASR 负责：视频里说了什么
LLM 负责：这些内容是什么意思，以及如何整理和重新表达
文件系统负责：源文件、结果文件和归档文件的生命周期
SQLite 负责：所有业务记录、版本、状态和历史追踪
```

因此，未来替换：

```text
SenseVoice → Whisper / WhisperX / Paraformer
DeepSeek   → GPT / Claude / Gemini / 本地大模型
```

都不应破坏本地文件扫描、任务管理、结果保存和文件转移记录能力。
