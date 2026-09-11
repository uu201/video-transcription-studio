# 视频转文案工作台

本地化音视频转文案工具，使用 SenseVoice 进行离线语音识别。

## 技术栈

### 后端
- Python 3.10+
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

### 1. 安装 Python 依赖

```bash
python -m pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 开发模式

**前后端分离开发（推荐）：**

终端 1 - 启动后端：
```bash
python run.py
# 后端运行在 http://localhost:8000
```

终端 2 - 启动前端：
```bash
cd frontend
npm run dev
# 前端运行在 http://localhost:5173
# 自动代理 API 请求到后端
```

### 4. 生产模式

**构建前端并通过 Python 启动：**

```bash
# 1. 构建前端
cd frontend
npm run build
# 构建产物输出到 app/static/dist

# 2. 启动 Python（包含前端）
cd ..
python run.py
# 访问 http://localhost:8000
```

## 开发说明

### 前端开发

```bash
cd frontend
npm run dev      # 开发模式
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

前端开发时，Vite 会自动代理 `/api` 和 `/ws` 请求到 `http://localhost:8000`

### 添加新功能

1. **添加 API 路由**：在 `app/api/` 下添加新的路由文件
2. **添加前端页面**：在 `frontend/src/views/` 下创建 Vue 组件
3. **添加状态管理**：在 `frontend/src/stores/` 下创建 Pinia store
4. **添加 API 调用**：在 `frontend/src/api/index.js` 中添加方法

## 环境要求

- Python 3.10+
- Node.js 18+
- FFmpeg（用于音视频处理）
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
```bash
python -m pip install -r requirements.txt
```

### 3. FFmpeg 不可用

- Windows: 下载 FFmpeg 并添加到 PATH
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## 许可证

MIT
