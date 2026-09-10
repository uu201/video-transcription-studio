# 视频转文案 - 本地音视频内容处理平台

基于 [SenseVoice](https://github.com/QwenAudio/SenseVoice) 和 [FunASR](https://github.com/modelscope/FunASR) 的本地视频转文案工具，支持批量处理、实时进度监控和多格式导出。

## ✨ 特性

- 🎯 **完全本地化**：数据不上传，隐私安全有保障
- 🚀 **批量处理**：扫描目录，手动选择文件批量创建任务
- 📊 **实时监控**：WebSocket 实时更新任务进度和状态
- 💾 **多格式导出**：支持 TXT、JSON、SRT 字幕格式
- 🔄 **智能重试**：失败任务可一键重试
- 🎨 **现代界面**：Vue 3 + Element Plus，深色模式支持

## 🚀 快速开始

### 环境要求

- Python 3.10 / 3.11 / 3.13
- FFmpeg 和 FFprobe（自动检测系统路径）
- 推荐 8GB+ 内存，支持 CPU 和 GPU 加速

### 安装运行

1. 克隆项目并创建虚拟环境：

```powershell
git clone <repository-url>
cd 视频转文案
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. 安装依赖：

```powershell
pip install -r requirements.txt
```

3. 启动应用：

```powershell
python start.py
```

4. 打开浏览器访问：<http://127.0.0.1:8000>

首次启动会自动：
- 创建数据库 `data/video_content.db`
- 检查系统环境（Python、FunASR、FFmpeg 等）
- 下载 SenseVoice 模型（约 420MB，自动缓存）

## 📖 使用流程

### 1. 配置扫描源

在”扫描源”页面添加本地媒体目录：
- 输入扫描源名称（如”本周素材”）
- 输入目录绝对路径（支持 Windows/Linux/macOS）
- 选择是否递归扫描子目录
- 设置文件稳定等待时间（防止扫描到正在复制的文件）

### 2. 扫描并选择文件

点击”立即扫描”按钮：
- 系统扫描目录发现媒体文件（mp4/mov/mp3/wav 等）
- 弹出文件选择对话框
- 勾选需要处理的文件（支持全选）
- 点击”创建任务”批量加入处理队列

### 3. 监控处理进度

在”处理任务”页面：
- 实时查看任务状态（待处理/处理中/已完成/失败）
- 查看详细进度和当前处理阶段
- 失败任务可查看错误详情并重试

### 4. 导出结果

任务完成后：
- 查看转写文本（原始文本和清洗后文本）
- 查看时间戳分段
- 导出为 TXT、JSON 或 SRT 字幕格式

## 🔧 环境变量配置

可选的环境变量：

```bash
# FFmpeg 路径（不设置则使用系统路径）
VIDEO_TEXT_FFMPEG_DIR=/path/to/ffmpeg

# 模型缓存目录（默认 ~/.cache/modelscope）
MODELSCOPE_CACHE=/path/to/models

# 数据库路径（默认 data/video_content.db）
VIDEO_TEXT_DATABASE=data/video_content.db

# Worker 并发数（默认 1）
VIDEO_TEXT_WORKER_COUNT=2
```

## 📁 项目结构

```
视频转文案/
├── app/
│   ├── api/              # FastAPI 路由
│   ├── services/         # 业务逻辑（扫描、ASR、任务处理）
│   ├── workers/          # 后台任务 Worker
│   ├── templates/        # 前端页面（Vue 单页应用）
│   └── static/          # 静态资源（CSS、JS）
├── data/                # 数据库文件
├── doc/                 # 架构和开发文档
├── requirements.txt     # Python 依赖
└── start.py            # 启动脚本
```

## 🚀 性能优化

本项目经过两个阶段的深度性能优化：

### 阶段一：基础优化
- ✅ 数据库索引优化 - 查询速度提升 50-80%
- ✅ 文件扫描优化 - 扫描速度提升 10 倍+
- ✅ 环境检测缓存 - 响应时间从 1-2s 降至 <10ms
- ✅ 前端代码模块化 - 代码可维护性大幅提升
- ✅ WebSocket 优化 - 连接更稳定，消息节流处理

### 阶段二：架构升级
- ✅ 多 Worker 并发 - 任务处理能力提升 2-3 倍
- ✅ 错误处理标准化 - 12 种业务异常类型
- ✅ 性能监控工具 - 自动记录关键路径执行时间
- ✅ 单元测试框架 - 17 个测试用例覆盖核心逻辑

### 阶段三：体验优化
- ✅ 智能错误提示 - 用户友好的错误消息
- ✅ 批量操作确认 - 防止误操作
- ✅ 加载状态优化 - 骨架屏和进度提示
- ✅ 操作节流防抖 - 防止重复提交

详见 [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)

## 🧪 运行测试

```bash
# 安装测试依赖
pip install -r requirements-dev.txt

# 运行所有测试
pytest tests/ -v

# 查看测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| VIDEO_TEXT_FFMPEG_DIR | FFmpeg 路径 | 系统 PATH |
| VIDEO_TEXT_DATABASE | 数据库路径 | data/video_content.db |
| VIDEO_TEXT_WORKER_COUNT | Worker 并发数 | 2 |
| MODELSCOPE_CACHE | 模型缓存目录 | ~/.cache/modelscope |

### 配置文件

编辑 `config/app.yaml` 自定义配置：

```yaml
worker:
  worker_count: 2  # Worker 并发数
  poll_interval_seconds: 2
  
asr:
  device: cpu  # 或 cuda:0
  language: auto
  batch_size_s: 30
```

## 🛠️ 技术栈

### 后端
- **FastAPI** - 高性能 Web 框架
- **SQLite** - 轻量级数据库
- **FunASR + SenseVoice** - 语音识别引擎
- **FFmpeg** - 音视频处理

### 前端
- **Vue 3** - 渐进式 JavaScript 框架
- **Element Plus** - UI 组件库
- **WebSocket** - 实时通信

### 测试
- **pytest** - 单元测试框架
- **pytest-asyncio** - 异步测试支持
- **pytest-cov** - 代码覆盖率

## 📚 架构文档

详细的架构设计和开发文档：

- [产品需求文档](<doc/视频文案提取与 AI 内容分析平台——需求文档.md>)
- [系统架构设计](doc/系统架构设计.md)
- [开发文档](doc/开发文档.md)

## 🔌 命令行工具（CLI）

项目包含独立的命令行工具 `video_to_text.py`，适合单文件快速处理：

```powershell
# 基本用法
python video_to_text.py "你的文件.mp4"

# 指定输出文件
python video_to_text.py "你的文件.mp4" -o "文案.txt"

# 指定语言和设备
python video_to_text.py "你的文件.mp4" --language zh --device cuda:0

# 同时保存原始 JSON
python video_to_text.py "你的文件.mp4" -o "文案.txt" --json "result.json"
```

支持的语言参数：`auto`、`zh`、`en`、`yue`、`ja`、`ko`、`nospeech`

## 🐛 常见问题

### FFmpeg 未找到
确保 FFmpeg 已安装并在系统 PATH 中，或设置 `VIDEO_TEXT_FFMPEG_DIR` 环境变量。

### FunASR 模块缺失
```powershell
pip install -r requirements.txt
```

### GPU 加速
如需使用 GPU，请根据 CUDA 版本安装匹配的 PyTorch：
```powershell
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 模型下载慢
首次运行会从 ModelScope 下载 SenseVoice 模型（~420MB）。如下载慢，可设置镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📝 待办事项

- [ ] AI Provider 集成（OpenAI/Ollama）
- [ ] 多语言混合识别优化
- [ ] 说话人分离
- [ ] 批量导出功能
- [ ] Docker 部署支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
