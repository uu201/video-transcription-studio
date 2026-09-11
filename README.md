# 视频转文案工作台

本地化音视频转文案工具，使用 SenseVoice 进行离线语音识别。

## 技术栈

### 后端
- Python 3.10 - 3.12（推荐 3.11）
- FastAPI
- SQLite
- FunASR (SenseVoice)
- FFmpeg

### 前端
- Vue 3
- Vite
- Naive UI
- Pinia
- Axios

## 项目结构

```
├── app/                    # Python 后端
│   ├── api/               # API 路由
│   ├── services/          # 业务逻辑
│   ├── db/                # 数据库
│   └── static/            # 静态文件（前端构建产物）
├── frontend/              # Vue 3 前端
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── stores/       # Pinia 状态管理
│   │   ├── api/          # API 请求
│   │   └── router/       # 路由配置
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── config/                # 配置文件
├── requirements.txt       # Python 依赖
└── README.md
```

## 快速开始

### 1. 检查运行环境

本项目当前支持以下环境：

| 条件 | 要求 |
| --- | --- |
| Python | 3.10、3.11 或 3.12，推荐 3.11 |
| Python 架构 | 64 位（Windows x64） |
| Node.js | 18 或更高版本 |
| FFmpeg | Windows x64 版本已随项目内置；其他平台需提供对应工具 |
| 内存 | 推荐 8 GB 以上 |
| 磁盘 | 预留模型缓存和临时音频空间 |

Python 3.13 及更高版本暂不支持。项目固定 `numpy<=1.26.4`，在 Python 3.13 的 Windows 环境中可能安装 NumPy 的 MinGW 实验构建，导致 FunASR 启动警告或崩溃。

Windows PowerShell 中先确认 Python 版本：

```powershell
py -0p
py -3.11 --version
```

如果没有 Python 3.10-3.12，请先安装其中一个版本。推荐使用 Python 3.11。

### 2. 创建虚拟环境并安装 Python 依赖

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import sys; print(sys.version); import numpy; print('numpy', numpy.__version__)"
```

不要使用系统 `python -m pip` 安装项目依赖，确保安装和启动都使用 `.venv\Scripts\python.exe`。

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 开发模式

**前后端分离开发（推荐）：**

终端 1 - 启动后端：
```bash
.venv\Scripts\python.exe start.py
# 后端运行在 http://localhost:8100
```

终端 2 - 启动前端：
```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
# 自动代理 API 请求到后端
```

### 5. 生产模式

**构建前端并通过 Python 启动：**

```bash
# 1. 构建前端
cd frontend
npm run build
# 构建产物输出到 app/static/dist

# 2. 启动 Python（包含前端）
cd ..
.venv\Scripts\python.exe start.py
# 访问 http://localhost:8100
```

## 开发说明

### 前端开发

```bash
cd frontend
npm run dev      # 开发模式
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

前端开发时，Vite 会自动代理 `/api` 和 `/ws` 请求到 `http://127.0.0.1:8100`

### 添加新功能

1. **添加 API 路由**：在 `app/api/` 下添加新的路由文件
2. **添加前端页面**：在 `frontend/src/views/` 下创建 Vue 组件
3. **添加状态管理**：在 `frontend/src/stores/` 下创建 Pinia store
4. **添加 API 调用**：在 `frontend/src/api/index.js` 中添加方法

## 环境要求

- Python 3.10 - 3.12（推荐 3.11）
- Python 3.13 及更高版本不支持
- Windows 使用 64 位 Python；不要混用系统 Python 和项目虚拟环境
- Node.js 18+
- 媒体工具：Windows 生产模式直接使用项目内置的 `runtime/ffmpeg/windows-x64/ffmpeg.exe` 和 `ffprobe.exe`；macOS/Linux 需要补充对应平台目录，或设置 `VIDEO_TEXT_FFMPEG_DIR`
- 首次识别需要下载 SenseVoice 和 FSMN-VAD 模型；请预留网络和磁盘空间
- 推荐 8GB+ 内存

## 配置

配置文件位于 `config/app.yaml`：

```yaml
root_dir: .
database_path: ./data/state.db
model_dir: ./models
asr_model: sensevoice
asr_device: cpu
worker_count: 2
```

## 常见问题

### 1. 前端黑屏或加载失败

确保已安装前端依赖并正确构建：
```bash
cd frontend
npm install
npm run build
```

### 2. FunASR 模块未找到

安装 Python 依赖：
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. NumPy 出现 `MINGW-W64` 或 `getlimits.py` 警告

这表示当前虚拟环境通常使用了 Python 3.13，而项目固定的 NumPy 1.26.x 没有对应的官方 Windows wheel。请使用 Python 3.11 重建环境：

```powershell
deactivate  # 如果当前已激活旧环境
Remove-Item -Recurse -Force .venv
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start.py
```

### 4. FFmpeg 不可用

主应用默认从 `runtime/ffmpeg/<平台目录>/` 查找 `ffmpeg` 和 `ffprobe`，不要求 Windows 用户另行安装 FFmpeg。当前仓库已提供：

```text
runtime/ffmpeg/windows-x64/ffmpeg.exe
runtime/ffmpeg/windows-x64/ffprobe.exe
```

如果使用 macOS/Linux，或需要指定外部版本，可以设置工具目录：

```powershell
$env:VIDEO_TEXT_FFMPEG_DIR = "D:\\tools\\ffmpeg"
.\.venv\Scripts\python.exe start.py
```

独立脚本 `video_to_text.py` 目前通过系统 PATH 查找 `ffmpeg`；直接运行该脚本时仍需安装 FFmpeg 或将其加入 PATH。

## 许可证

MIT
