# 视频转文案工作台 - 前端开发指南

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **Naive UI** - Vue 3 组件库
- **Pinia** - Vue 状态管理
- **Vue Router** - 官方路由
- **Axios** - HTTP 客户端

## 目录结构

```
frontend/
├── src/
│   ├── api/              # API 请求封装
│   │   └── index.js      # API 方法
│   ├── assets/           # 静态资源
│   ├── components/       # 公共组件
│   ├── router/           # 路由配置
│   │   └── index.js
│   ├── stores/           # Pinia 状态管理
│   │   ├── app.js        # 全局应用状态
│   │   ├── source.js     # 扫描源状态
│   │   └── task.js       # 任务状态
│   ├── utils/            # 工具函数
│   ├── views/            # 页面组件
│   │   ├── Workspace.vue      # 主布局
│   │   ├── Overview.vue       # 总览页
│   │   ├── Sources.vue        # 扫描源页
│   │   ├── Tasks.vue          # 任务列表页
│   │   ├── TaskDetail.vue     # 任务详情页
│   │   └── Settings.vue       # 设置页
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html            # HTML 模板
├── vite.config.js        # Vite 配置
├── package.json          # 依赖配置
└── .npmrc               # npm 配置
```

## 开发流程

### 1. 安装依赖

```bash
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端开发服务器会运行在 `http://localhost:5173`，并自动代理 API 请求到后端 `http://localhost:8000`。

**确保后端已启动：**
```bash
# 在另一个终端
python run.py
```

### 3. 构建生产版本

```bash
npm run build
```

构建产物会输出到 `../app/static/dist`，然后可以通过 Python 后端访问。

## API 请求

所有 API 请求通过 `src/api/index.js` 统一管理：

```javascript
import api from '@/api'

// 获取任务列表
const tasks = await api.getTasks()

// 获取任务详情
const task = await api.getTaskDetail(id)
```

### 可用的 API 方法

- **系统信息**
  - `getSystemInfo()` - 获取系统信息
  - `getEnvironment(force)` - 获取环境检测结果
  - `checkMediaTools()` - 检查 FFmpeg 工具

- **扫描源**
  - `getSources()` - 获取扫描源列表
  - `createSource(data)` - 创建扫描源
  - `updateSource(id, data)` - 更新扫描源
  - `deleteSource(id)` - 删除扫描源
  - `scanSource(id)` - 扫描指定源

- **任务**
  - `getTasks(params)` - 获取任务列表
  - `getTaskDetail(id)` - 获取任务详情
  - `createTasks(data)` - 批量创建任务
  - `retryTask(id)` - 重试任务
  - `cancelTask(id)` - 取消任务
  - `deleteTask(id)` - 删除任务

- **导出**
  - `exportTranscript(taskId, format)` - 导出转写结果

## 状态管理

使用 Pinia 进行状态管理，每个 store 负责一个功能模块：

### App Store (`stores/app.js`)

```javascript
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

// 主题切换
appStore.toggleTheme()

// 当前主题
console.log(appStore.isDark)
```

### Task Store (`stores/task.js`)

```javascript
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()

// 获取任务列表
await taskStore.fetchTasks()

// 任务统计
console.log(taskStore.taskStats)

// 重试任务
await taskStore.retryTask(id)
```

### Source Store (`stores/source.js`)

```javascript
import { useSourceStore } from '@/stores/source'

const sourceStore = useSourceStore()

// 获取扫描源
await sourceStore.fetchSources()

// 创建扫描源
await sourceStore.createSource(data)

// 扫描
await sourceStore.scanSource(id)
```

## 路由配置

路由配置在 `src/router/index.js`：

- `/` - 主布局（Workspace）
  - `/overview` - 总览
  - `/sources` - 扫描源
  - `/tasks` - 任务列表
  - `/tasks/:id` - 任务详情
  - `/settings` - 设置

## 组件使用

项目使用 Naive UI 组件库，所有组件可以直接使用：

```vue
<template>
  <n-button type="primary" @click="handleClick">
    点击我
  </n-button>
  
  <n-card title="卡片标题">
    卡片内容
  </n-card>
</template>
```

常用组件：
- `n-button` - 按钮
- `n-card` - 卡片
- `n-input` - 输入框
- `n-select` - 选择器
- `n-table` / `n-data-table` - 表格
- `n-form` / `n-form-item` - 表单
- `n-space` - 间距容器
- `n-grid` / `n-gi` - 栅格布局

文档：https://www.naiveui.com/

## 开发规范

### 1. 文件命名

- 组件文件：PascalCase（如 `TaskDetail.vue`）
- JS 文件：camelCase（如 `index.js`）
- Store 文件：camelCase（如 `task.js`）

### 2. 组件结构

```vue
<template>
  <!-- 模板 -->
</template>

<script setup>
// 使用 Composition API 的 script setup 语法
import { ref, onMounted } from 'vue'

// 响应式数据
const count = ref(0)

// 方法
function increment() {
  count.value++
}

// 生命周期
onMounted(() => {
  console.log('组件已挂载')
})
</script>

<style scoped>
/* 样式 */
</style>
```

### 3. API 调用

统一使用 try-catch 处理错误：

```javascript
import { useMessage } from 'naive-ui'

const message = useMessage()

async function loadData() {
  try {
    const data = await api.getTasks()
    // 处理数据
  } catch (error) {
    message.error('加载失败')
  }
}
```

## 常见问题

### 1. API 请求失败

确保后端已启动在 `http://localhost:8000`。

### 2. 热更新不生效

重启开发服务器：
```bash
npm run dev
```

### 3. 构建失败

清除缓存并重新安装依赖：
```bash
rm -rf node_modules package-lock.json
npm install
```

## 生产部署

1. 构建前端：
```bash
npm run build
```

2. 启动 Python 后端（自动提供前端）：
```bash
python run.py
```

3. 访问 `http://localhost:8000`
