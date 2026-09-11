<div align="center">

# Video Transcription Studio

### 视频转文案工作台 · 本地化音视频转录工具

<p>
  基于 SenseVoice 的离线语音识别，为内容创作者提供高质量的音视频转文字服务
</p>

<p>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=flat-square" />
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10--3.12-3776ab?style=flat-square&logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img alt="Vue" src="https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js&logoColor=white" />
  <img alt="Vite" src="https://img.shields.io/badge/Vite-6-646cff?style=flat-square&logo=vite&logoColor=white" />
</p>

<p>
  <a href="#-功能概览">功能概览</a> ·
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-技术栈">技术栈</a> ·
  <a href="#-开发说明">开发说明</a>
</p>

</div>

---

## ✨ 项目简介

Video Transcription Studio 是一款专注于本地化处理的音视频转录工具，无需依赖云端服务，完全保护隐私。

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>🏠 本地优先</h4>
      <p>所有音视频处理和识别均在本地完成，数据不上传任何第三方服务，完全掌控隐私安全。</p>
    </td>
    <td width="50%" valign="top">
      <h4>⚡ 高效转录</h4>
      <p>基于 FunASR 的 SenseVoice 模型，支持多语言识别，提供高质量的转录结果。</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h4>📊 任务管理</h4>
      <p>支持批量任务队列、任务暂停/恢复、进度跟踪，服务重启后自动恢复未完成任务。</p>
    </td>
    <td width="50%" valign="top">
      <h4>📚 结果书架</h4>
      <p>转录结果以书架形式展示，支持检索、导出，方便管理和复用历史转录内容。</p>
    </td>
  </tr>
  <tr>
    <td colspan="2" valign="top">
      <h4>🎬 媒体格式支持</h4>
      <p>支持主流音视频格式（MP4、MP3、WAV、M4A 等），内置 FFmpeg 自动提取音频流。</p>
    </td>
  </tr>
</table>

## 🚀 功能概览

<details open>
<summary><b>🎯 核心功能</b></summary>

- **音视频转录**：上传音视频文件，自动提取音频并进行语音识别
- **批量处理**：支持多文件同时上传，队列化处理
- **实时进度**：WebSocket 实时推送转录进度和状态
- **任务恢复**：服务重启后自动恢复未完成的任务
- **结果管理**：转录结果归档展示，支持搜索和导出

</details>

<details open>
<summary><b>🛠️ 技术特性</b></summary>

- **离线模型**：使用 FunASR SenseVoice 本地模型，首次运行自动下载
- **多语言支持**：支持中文、英文等多种语言的语音识别
- **时间戳对齐**：生成带时间戳的转录文本，方便定位
- **任务重试**：失败任务支持重新转录
- **进度跟踪**：详细的任务状态和进度信息

</details>

## 🧱 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Python 3.10-3.12 |
| 前端框架 | Vue 3 + TypeScript |
| 状态管理 | Pinia |
| UI 组件库 | Naive UI |
| 构建工具 | Vite 6 |
| 持久化 | SQLite |
| 语音识别 | FunASR (SenseVoice + FSMN-VAD) |
| 媒体处理 | FFmpeg |
| 实时通信 | WebSocket |

## 📋 环境要求

- **Python** 3.10、3.11 或 3.12（推荐 3.11）
  - ⚠️ Python 3.13+ 暂不支持（NumPy 兼容性问题）
  - 必须使用 64 位 Python（Windows x64）
- **Node.js** 18+
- **FFmpeg**：Windows 已内置在 `runtime/ffmpeg/windows-x64/`
- **内存**：推荐 8 GB 以上
- **磁盘**：预留模型缓存空间（首次运行自动下载）

## ⚡ 快速开始

### 1. 检查 Python 版本

```powershell
# 列出已安装的 Python 版本
py -0p

# 确认 Python 3.11 可用
py -3.11 --version
```

如果没有 Python 3.10-3.12，请先安装其中一个版本。

### 2. 创建虚拟环境并安装后端依赖

```powershell
# 创建虚拟环境
py -3.11 -m venv .venv

# 升级 pip
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 安装依赖
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 验证安装
.\.venv\Scripts\python.exe -c "import sys; print(sys.version); import numpy; print('numpy', numpy.__version__)"
```

⚠️ **重要**：不要使用系统 Python 安装依赖，确保所有命令都使用 `.venv\Scripts\python.exe`

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 开发模式（推荐）

**终端 1 - 启动后端：**
```bash
.venv\Scripts\python.exe start.py
# 后端运行在 http://localhost:8100
```

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
# 自动代理 API 请求到后端
```

### 5. 生产模式

```bash
# 1. 构建前端
cd frontend
npm run build
# 构建产物输出到 app/static/dist

# 2. 启动服务（包含前端）
cd ..
.venv\Scripts\python.exe start.py
# 访问 http://localhost:8100
```

## 📁 项目结构

<details>
<summary>点击展开完整目录树</summary>

```
video-transcription-studio/
├── app/                        # Python 后端
│   ├── api/                   # FastAPI 路由
│   │   ├── tasks.py          # 任务管理 API
│   │   ├── transcripts.py    # 转录结果 API
│   │   └── websocket.py      # WebSocket 端点
│   ├── services/              # 业务逻辑
│   │   ├── task_service.py   # 任务调度与执行
│   │   └── asr_service.py    # 语音识别服务
│   ├── db/                    # 数据库
│   │   ├── database.py       # SQLite 连接
│   │   └── models.py         # 数据模型
│   ├── static/                # 前端构建产物
│   └── main.py                # FastAPI 应用入口
├── frontend/                   # Vue 3 前端
│   ├── src/
│   │   ├── views/            # 页面组件
│   │   │   ├── HomeView.vue  # 任务管理页
│   │   │   └── ShelfView.vue # 转录书架页
│   │   ├── stores/           # Pinia 状态管理
│   │   │   ├── task.ts       # 任务状态
│   │   │   └── shelf.ts      # 书架状态
│   │   ├── api/              # API 请求
│   │   │   └── index.ts      # API 封装
│   │   └── router/           # 路由配置
│   ├── vite.config.ts
│   └── package.json
├── config/                     # 配置文件
│   └── app.yaml               # 应用配置
├── runtime/                    # 运行时资源
│   └── ffmpeg/                # FFmpeg 工具
│       └── windows-x64/       # Windows 版本
├── data/                       # 数据目录（自动创建）
│   ├── state.db              # SQLite 数据库
│   ├── models/               # ASR 模型缓存
│   └── uploads/              # 上传文件
├── requirements.txt            # Python 依赖
├── start.py                    # 启动脚本
└── README.md
```

</details>

## 🏛️ 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI 后端                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ 任务队列  │  │  SQLite  │  │    ASR 服务          │  │
│  │          │  │ 持久化   │  │ SenseVoice + VAD     │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
├─────────────────── HTTP/WS ─────────────────────────────┤
│                    Vue 3 前端                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │  Pinia   │  │ Naive UI │  │   WebSocket 客户端   │  │
│  │  Store   │  │  组件    │  │                      │  │
│  └──────────┘  └──────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

> **数据流**：上传文件 → 后端队列化处理 → FFmpeg 提取音频 → SenseVoice 转录 → WebSocket 推送进度 → 结果存入 SQLite → 前端展示

## 🛠️ 开发说明

### 前端开发

```bash
cd frontend
npm run dev      # 开发模式（热重载）
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

前端开发时，Vite 会自动代理 `/api` 和 `/ws` 请求到 `http://127.0.0.1:8100`

### 后端开发

后端修改后需重启 `start.py`，支持热重载请使用：

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8100
```

### 添加新功能

1. **添加 API 路由**：在 `app/api/` 下添加新的路由文件
2. **添加服务逻辑**：在 `app/services/` 下实现业务逻辑
3. **添加前端页面**：在 `frontend/src/views/` 下创建 Vue 组件
4. **添加状态管理**：在 `frontend/src/stores/` 下创建 Pinia store
5. **添加 API 调用**：在 `frontend/src/api/index.ts` 中添加接口方法

## ⚙️ 配置说明

配置文件位于 `config/app.yaml`：

```yaml
root_dir: .                      # 项目根目录
database_path: ./data/state.db   # SQLite 数据库路径
model_dir: ./data/models         # ASR 模型缓存目录
asr_model: sensevoice            # 语音识别模型
asr_device: cpu                  # 运行设备（cpu/cuda）
worker_count: 2                  # 并发任务数
```

### 环境变量

- `VIDEO_TEXT_FFMPEG_DIR`：自定义 FFmpeg 工具目录（可选）

## 💾 数据存储

应用数据保存在本地：

- 📊 **数据库**：`./data/state.db`（SQLite）
- 📦 **模型缓存**：`./data/models/`（自动下载）
- 📁 **上传文件**：`./data/uploads/`
- 📝 **转录结果**：存储在 SQLite 中

> 🔒 所有数据完全本地，不上传任何第三方服务。

## 🔧 常见问题

<details>
<summary><b>1. 前端页面加载失败或黑屏</b></summary>

确保已正确构建前端：

```bash
cd frontend
npm install
npm run build
```

检查 `app/static/dist` 目录是否存在构建产物。

</details>

<details>
<summary><b>2. FunASR 模块未找到</b></summary>

使用虚拟环境的 Python 重新安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

</details>

<details>
<summary><b>3. NumPy 出现 MINGW-W64 警告或崩溃</b></summary>

这通常表示使用了 Python 3.13，请使用 Python 3.11 重建环境：

```powershell
deactivate  # 退出当前虚拟环境
Remove-Item -Recurse -Force .venv
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start.py
```

</details>

<details>
<summary><b>4. FFmpeg 不可用</b></summary>

Windows 平台已内置 FFmpeg 在 `runtime/ffmpeg/windows-x64/`。

如需使用自定义版本，设置环境变量：

```powershell
$env:VIDEO_TEXT_FFMPEG_DIR = "D:\tools\ffmpeg"
.\.venv\Scripts\python.exe start.py
```

macOS/Linux 需要补充对应平台目录或安装系统 FFmpeg。

</details>

<details>
<summary><b>5. 首次转录速度慢</b></summary>

首次运行时需要下载 SenseVoice 和 FSMN-VAD 模型（约 1GB），请耐心等待。模型下载完成后会缓存到本地，后续使用将直接加载。

</details>

## 📄 License

[MIT](./LICENSE) © zhouyeshan

<div align="center">

<sub>如果这个项目对你有帮助，欢迎 Star ⭐ 支持一下</sub>

</div>
