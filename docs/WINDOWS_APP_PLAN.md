# Windows 桌面应用方案

## 目标

将当前的 Web 应用打包成 Windows 桌面应用，提供更好的用户体验：
- ✅ 双击启动，无需手动运行 Python 命令
- ✅ 系统托盘图标，后台运行
- ✅ 开机自启动（可选）
- ✅ 独立窗口，类似原生应用
- ✅ 自动检查更新
- ✅ 一键安装/卸载

---

## 方案对比

### 方案 1：Electron（推荐 ⭐⭐⭐⭐⭐）

**优势**：
- ✅ 跨平台（Windows/Mac/Linux）
- ✅ 成熟的生态系统
- ✅ 丰富的 API（系统托盘、通知、文件对话框等）
- ✅ 自动更新支持完善
- ✅ 可以直接嵌入现有的前端代码

**劣势**：
- ⚠️ 安装包较大（~150-200MB）
- ⚠️ 内存占用较高（~100-150MB）

**适合场景**：需要跨平台、功能丰富、用户体验最佳

**开发成本**：⭐⭐⭐ 中等（1-2 周）

---

### 方案 2：Tauri（推荐 ⭐⭐⭐⭐）

**优势**：
- ✅ 安装包小（~10-20MB）
- ✅ 内存占用低（~30-50MB）
- ✅ 使用系统 WebView，无需打包浏览器
- ✅ Rust 编写，安全性高
- ✅ 跨平台

**劣势**：
- ⚠️ 生态相对较新
- ⚠️ 依赖系统 WebView（Windows 需要 Edge WebView2）
- ⚠️ 学习曲线稍陡

**适合场景**：追求小体积、低资源占用

**开发成本**：⭐⭐⭐⭐ 中高（1.5-3 周）

---

### 方案 3：PyInstaller + Flask/FastAPI + WebView

**优势**：
- ✅ 纯 Python，无需学习新语言
- ✅ 可以直接打包现有后端
- ✅ 开发成本最低

**劣势**：
- ⚠️ 安装包较大（~80-150MB）
- ⚠️ 功能有限（系统托盘、自动更新需要额外开发）
- ⚠️ 用户体验一般

**适合场景**：快速原型、内部工具

**开发成本**：⭐⭐ 低（3-7 天）

---

### 方案 4：NW.js

**优势**：
- ✅ 类似 Electron，但更轻量
- ✅ 可以直接访问 Node.js 模块

**劣势**：
- ⚠️ 生态不如 Electron 丰富
- ⚠️ 更新不如 Electron 频繁

**适合场景**：需要 Electron 功能但希望更轻量

**开发成本**：⭐⭐⭐ 中等（1-2 周）

---

## 推荐方案详解

### 🏆 方案 A：Electron（最佳用户体验）

#### 架构设计

```
┌─────────────────────────────────────────┐
│         Electron 主进程                  │
│  ┌────────────────────────────────────┐ │
│  │  - 启动 FastAPI 后端（子进程）      │ │
│  │  - 创建窗口                        │ │
│  │  - 系统托盘                        │ │
│  │  - 自动更新                        │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│         Electron 渲染进程                │
│  ┌────────────────────────────────────┐ │
│  │  加载 http://localhost:8100         │ │
│  │  (FastAPI + Vue 前端)              │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│         Python FastAPI 后端              │
│  - 打包为可执行文件（PyInstaller）      │
│  - 由 Electron 启动和管理               │
└─────────────────────────────────────────┘
```

#### 项目结构

```
video-transcriber-desktop/
├── electron/                    # Electron 主进程
│   ├── main.js                 # 主进程入口
│   ├── preload.js              # 预加载脚本
│   └── tray.js                 # 系统托盘
├── resources/                   # 打包资源
│   ├── icon.ico                # Windows 图标
│   ├── icon.png                # Linux/Mac 图标
│   └── backend/                # Python 后端可执行文件
│       └── app.exe             # PyInstaller 打包的后端
├── frontend/                    # 前端资源（可选，也可以从后端加载）
│   └── ...
├── package.json                # Electron 配置
├── electron-builder.json       # 打包配置
└── README.md
```

#### 核心代码示例

**electron/main.js**：
```javascript
const { app, BrowserWindow, Tray, Menu } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let mainWindow;
let backendProcess;
let tray;

// 启动 Python 后端
function startBackend() {
  const backendPath = path.join(
    process.resourcesPath,
    'backend',
    'app.exe'
  );
  
  backendProcess = spawn(backendPath, [], {
    cwd: path.dirname(backendPath)
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data}`);
  });
}

// 等待后端启动
function waitForBackend(callback, retries = 50) {
  http.get('http://localhost:8100/api/health', (res) => {
    if (res.statusCode === 200) {
      callback();
    } else {
      setTimeout(() => waitForBackend(callback, retries - 1), 100);
    }
  }).on('error', () => {
    if (retries > 0) {
      setTimeout(() => waitForBackend(callback, retries - 1), 100);
    } else {
      console.error('Failed to start backend');
      app.quit();
    }
  });
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    icon: path.join(__dirname, '../resources/icon.ico'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    frame: true,
    titleBarStyle: 'default'
  });

  mainWindow.loadURL('http://localhost:8100');

  // 窗口关闭时最小化到托盘
  mainWindow.on('close', (event) => {
    if (!app.isQuiting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

// 创建系统托盘
function createTray() {
  tray = new Tray(path.join(__dirname, '../resources/icon.ico'));
  
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        mainWindow.show();
      }
    },
    {
      label: '退出',
      click: () => {
        app.isQuiting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('视频转文案工具');
  tray.setContextMenu(contextMenu);
  
  tray.on('double-click', () => {
    mainWindow.show();
  });
}

// 应用启动
app.whenReady().then(() => {
  startBackend();
  
  waitForBackend(() => {
    createWindow();
    createTray();
  });
});

// 退出时清理
app.on('will-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

// macOS 特殊处理
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
```

**package.json**：
```json
{
  "name": "video-transcriber",
  "version": "1.0.0",
  "description": "本地视频转文案工具",
  "main": "electron/main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder",
    "build:win": "electron-builder --win",
    "pack:backend": "cd .. && pyinstaller --clean --onefile app/main.py"
  },
  "build": {
    "appId": "com.yourcompany.videotranscriber",
    "productName": "视频转文案工具",
    "directories": {
      "output": "dist"
    },
    "files": [
      "electron/**/*",
      "resources/**/*"
    ],
    "extraResources": [
      {
        "from": "resources/backend",
        "to": "backend"
      }
    ],
    "win": {
      "target": ["nsis", "portable"],
      "icon": "resources/icon.ico",
      "requestedExecutionLevel": "asInvoker"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "视频转文案工具"
    }
  },
  "dependencies": {
    "electron-squirrel-startup": "^1.0.0"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1"
  }
}
```

#### 开发步骤

1. **准备 Python 后端可执行文件**：
```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包后端
pyinstaller --clean --onefile \
  --hidden-import=uvicorn \
  --hidden-import=fastapi \
  --add-data "app/static:app/static" \
  --add-data "app/templates:app/templates" \
  --icon=resources/icon.ico \
  --name=VideoTranscriberBackend \
  app/main.py

# 输出在 dist/VideoTranscriberBackend.exe
```

2. **创建 Electron 项目**：
```bash
mkdir video-transcriber-desktop
cd video-transcriber-desktop
npm init -y
npm install electron electron-builder --save-dev
```

3. **开发和调试**：
```bash
# 开发模式（需要先启动 Python 后端）
npm start

# 打包
npm run build:win
```

#### 打包输出

- **安装包**：`dist/VideoTranscriber Setup 1.0.0.exe`（~200MB）
- **便携版**：`dist/VideoTranscriber 1.0.0.exe`（~200MB）

---

### 🎯 方案 B：Tauri（轻量级）

#### 架构设计

```
┌─────────────────────────────────────────┐
│         Tauri Core (Rust)               │
│  ┌────────────────────────────────────┐ │
│  │  - 启动 Python 后端                │ │
│  │  - WebView 窗口管理                │ │
│  │  - 系统托盘                        │ │
│  │  - IPC 通信                        │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────┐
│    WebView2 (系统自带)                   │
│  加载 http://localhost:8100              │
└─────────────────────────────────────────┘
```

#### 项目结构

```
video-transcriber-tauri/
├── src-tauri/                   # Tauri Rust 代码
│   ├── src/
│   │   └── main.rs             # Rust 主程序
│   ├── Cargo.toml              # Rust 依赖
│   ├── tauri.conf.json         # Tauri 配置
│   └── icons/                  # 应用图标
├── resources/
│   └── backend/
│       └── app.exe             # Python 后端
├── package.json
└── README.md
```

#### 核心代码示例

**src-tauri/src/main.rs**：
```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use tauri::{CustomMenuItem, SystemTray, SystemTrayMenu, SystemTrayEvent};
use tauri::Manager;

struct BackendProcess(Child);

// 启动 Python 后端
fn start_backend() -> Result<Child, std::io::Error> {
    let backend_path = std::env::current_exe()?
        .parent()
        .unwrap()
        .join("backend")
        .join("app.exe");
    
    Command::new(backend_path)
        .spawn()
}

fn main() {
    // 系统托盘菜单
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("show", "显示窗口"))
        .add_item(CustomMenuItem::new("quit", "退出"));
    
    let tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .system_tray(tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => {
                match id.as_str() {
                    "show" => {
                        let window = app.get_window("main").unwrap();
                        window.show().unwrap();
                        window.set_focus().unwrap();
                    }
                    "quit" => {
                        std::process::exit(0);
                    }
                    _ => {}
                }
            }
            SystemTrayEvent::DoubleClick { .. } => {
                let window = app.get_window("main").unwrap();
                window.show().unwrap();
            }
            _ => {}
        })
        .setup(|app| {
            // 启动后端
            let backend = start_backend().expect("Failed to start backend");
            app.manage(BackendProcess(backend));
            
            // 等待后端启动
            std::thread::sleep(std::time::Duration::from_secs(2));
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**src-tauri/tauri.conf.json**：
```json
{
  "build": {
    "beforeBuildCommand": "",
    "beforeDevCommand": "",
    "devPath": "http://localhost:8100",
    "distDir": "../dist"
  },
  "package": {
    "productName": "视频转文案工具",
    "version": "1.0.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "all": false,
        "open": true
      }
    },
    "bundle": {
      "active": true,
      "targets": ["msi", "nsis"],
      "identifier": "com.yourcompany.videotranscriber",
      "icon": [
        "icons/32x32.png",
        "icons/icon.ico"
      ],
      "resources": ["resources/backend/*"],
      "windows": {
        "certificateThumbprint": null,
        "digestAlgorithm": "sha256",
        "timestampUrl": ""
      }
    },
    "windows": [
      {
        "title": "视频转文案工具",
        "width": 1400,
        "height": 900,
        "resizable": true,
        "fullscreen": false
      }
    ]
  }
}
```

#### 开发步骤

1. **安装 Tauri CLI**：
```bash
npm install -g @tauri-apps/cli
cargo install tauri-cli
```

2. **创建项目**：
```bash
npm create tauri-app
# 或
cargo create-tauri-app
```

3. **开发和打包**：
```bash
# 开发模式
npm run tauri dev

# 打包
npm run tauri build
```

#### 打包输出

- **安装包**：`target/release/bundle/msi/VideoTranscriber_1.0.0_x64.msi`（~15MB）
- **NSIS 安装包**：`target/release/bundle/nsis/VideoTranscriber_1.0.0_x64-setup.exe`（~15MB）

---

### ⚡ 方案 C：PyInstaller + pywebview（快速实现）

#### 架构设计

```
┌─────────────────────────────────────────┐
│         Python 主程序                    │
│  ┌────────────────────────────────────┐ │
│  │  - FastAPI 后端（threading）        │ │
│  │  - pywebview 窗口                  │ │
│  │  - 系统托盘（pystray）              │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### 核心代码

**main_desktop.py**：
```python
import webview
import threading
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app as fastapi_app
import uvicorn

def start_backend():
    """在后台线程启动 FastAPI"""
    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=8100,
        log_level="error"
    )

def create_window():
    """创建桌面窗口"""
    # 启动后端
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # 等待后端启动
    import time
    time.sleep(2)
    
    # 创建窗口
    window = webview.create_window(
        '视频转文案工具',
        'http://localhost:8100',
        width=1400,
        height=900,
        resizable=True,
        min_size=(1200, 700)
    )
    
    webview.start()

if __name__ == '__main__':
    create_window()
```

**requirements-desktop.txt**：
```
pywebview[winforms]  # Windows
pystray              # 系统托盘
pillow              # 图标处理
```

**打包脚本 build-windows.spec**：
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/static', 'app/static'),
        ('app/templates', 'app/templates'),
        ('data', 'data'),
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.protocols',
        'fastapi',
        'webview',
        'clr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VideoTranscriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico'
)
```

**打包命令**：
```bash
# 安装依赖
pip install -r requirements-desktop.txt
pip install pyinstaller

# 打包
pyinstaller build-windows.spec

# 输出：dist/VideoTranscriber.exe
```

---

## 功能对比表

| 功能 | Electron | Tauri | PyWebview | NW.js |
|------|---------|-------|-----------|-------|
| **安装包大小** | ~200MB | ~15MB | ~100MB | ~180MB |
| **内存占用** | ~150MB | ~50MB | ~80MB | ~130MB |
| **启动速度** | 快 | 很快 | 快 | 快 |
| **系统托盘** | ✅ 完善 | ✅ 完善 | ✅ 需额外库 | ✅ 完善 |
| **自动更新** | ✅ 完善 | ✅ 完善 | ❌ 需自己实现 | ⚠️ 有限 |
| **跨平台** | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux |
| **开发成本** | 中等 | 中高 | 低 | 中等 |
| **社区支持** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **学习曲线** | 平缓 | 陡峭 | 平缓 | 平缓 |

---

## 最终推荐

### 🥇 首选：Electron
**适合大多数场景，功能完善，生态成熟**

**优点**：
- 用户体验最佳
- 功能最完善（托盘、更新、通知等）
- 文档和示例丰富
- 易于调试

**缺点**：
- 安装包较大

### 🥈 次选：Tauri
**追求小体积和低资源占用**

**优点**：
- 安装包小 10 倍
- 内存占用低
- 现代化技术栈

**缺点**：
- 需要学习 Rust
- 依赖系统 WebView2

### 🥉 备选：PyWebview
**快速原型或内部工具**

**优点**：
- 开发最快（纯 Python）
- 代码改动最少

**缺点**：
- 功能有限
- 用户体验一般

---

## 实施计划

### 第一阶段：验证方案（2-3 天）

1. **选择方案**：建议先选 Electron
2. **创建 POC**：
   - 打包 Python 后端为 exe
   - 创建最小 Electron 项目
   - 验证启动和通信

### 第二阶段：功能开发（1-2 周）

1. **核心功能**：
   - 窗口管理
   - 后端进程管理
   - 错误处理

2. **增强功能**：
   - 系统托盘
   - 开机自启动
   - 配置持久化

3. **打包配置**：
   - 图标和资源
   - 安装包配置
   - 签名（可选）

### 第三阶段：测试和优化（3-5 天）

1. **功能测试**
2. **性能优化**
3. **安装/卸载测试**
4. **用户文档**

---

## 开发资源

### Electron
- 官方文档：https://www.electronjs.org/
- 示例项目：https://github.com/electron/electron-quick-start
- 打包工具：https://www.electron.build/

### Tauri
- 官方文档：https://tauri.app/
- 快速开始：https://tauri.app/v1/guides/getting-started/setup/
- 示例：https://github.com/tauri-apps/tauri/tree/dev/examples

### PyWebview
- 官方文档：https://pywebview.flowrl.com/
- GitHub：https://github.com/r0x0r/pywebview

---

## 预期效果

用户视角：
1. ✅ 双击桌面图标启动
2. ✅ 3-5 秒后应用窗口打开
3. ✅ 关闭窗口后最小化到托盘继续运行
4. ✅ 右键托盘图标可退出
5. ✅ 一键安装，无需配置 Python 环境

技术视角：
1. ✅ 前端和后端都打包在应用内
2. ✅ 数据存储在用户文档目录
3. ✅ 支持静默更新
4. ✅ 完整的错误处理和日志

---

## 下一步

请告诉我：
1. **优先级**：希望先实现哪些功能？
2. **用户群体**：主要用户是谁？（个人用户/企业内部）
3. **分发方式**：如何分发？（官网下载/企业内网）
4. **方案偏好**：倾向于 Electron（完善）还是 Tauri（轻量）？

我可以帮你：
- 创建完整的项目模板
- 编写打包脚本
- 实现系统托盘和自动更新
- 优化性能和体积
