# 视频转文案

使用 [QwenAudio/SenseVoice](https://github.com/QwenAudio/SenseVoice) 官方模型说明，
通过 [FunASR](https://github.com/modelscope/FunASR) 加载 SenseVoiceSmall，将视频或音频转成文案文本。

当前项目正在从独立 CLI 演进为本地视频内容处理平台，产品范围、系统架构和开发步骤已经整理到 `doc/`。

## 启动本地平台

使用 Python 3.10/3.11（当前代码也兼容 Python 3.13）创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python start.py
```

浏览器打开 <http://127.0.0.1:8000>。首次启动会创建 `data/video_content.db`；在“扫描源”页面配置本地目录后，Worker 会在后台创建任务。正式转写前请把对应平台的 `ffmpeg` 和 `ffprobe` 放入 `runtime/ffmpeg/`，或使用 `VIDEO_TEXT_FFMPEG_DIR` 指定开发目录。

应用首页、扫描源、任务详情和导出接口已经可运行；AI Provider 与文件归档保留了独立接口，默认不会阻断 ASR 主链路。

## 架构文档

- [产品需求文档](<doc/视频文案提取与 AI 内容分析平台——需求文档.md>)
- [系统架构设计](doc/系统架构设计.md)
- [开发文档](doc/开发文档.md)

目标能力包括：本地目录扫描、内置 FFmpeg、独立 SenseVoice ASR、SQLite 任务与结果记录、可替换 AI Provider、文本导出和文件转移历史。

## 准备环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

正式应用会在发布包中内置当前平台的 `ffmpeg` 和 `ffprobe`，用户不需要单独安装或配置 `PATH`。

`video_to_text.py` 是独立的命令行参考工具，不属于正式应用后端实现。当前直接运行该脚本时仍需要系统中可用的 `ffmpeg`；正式应用将通过 `MediaToolchain` 使用发布包内置版本。

如果你想用 GPU，请按自己的 CUDA 版本安装匹配的 PyTorch；脚本会在可用时自动选择 `cuda:0`，否则使用 CPU。

## 使用

```powershell
python video_to_text.py "你的文件.mp4"
```

默认输出到同目录的 `你的文件.txt`。

指定输出文件：

```powershell
python video_to_text.py "你的文件.mp4" -o "文案.txt"
```

指定语言和设备：

```powershell
python video_to_text.py "你的文件.mp4" --language zh --device cuda:0
```

同时保存原始 JSON：

```powershell
python video_to_text.py "你的文件.mp4" -o "文案.txt" --json "result.json"
```

常用语言参数：`auto`、`zh`、`en`、`yue`、`ja`、`ko`、`nospeech`。
