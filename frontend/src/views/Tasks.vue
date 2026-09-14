<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">转录任务</h1>
        <n-text depth="3">实时跟踪转录进度，管理转录和 AI 分析任务</n-text>
      </div>
      <n-space align="center">
        <n-tag :type="realtimeConnected ? 'success' : 'warning'" size="small" round>
          <span class="realtime-dot" :class="{ connected: realtimeConnected }"></span>
          {{ realtimeConnected ? '实时连接' : '正在重连' }}
        </n-tag>
        <n-button :loading="taskStore.loading" @click="taskStore.fetchTasks">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新列表
        </n-button>
      </n-space>
    </div>

    <!-- 正在处理的任务 -->
    <section v-if="activeTasks.length" class="active-workspace">
      <div class="active-workspace-heading">
        <div>
          <span class="section-kicker">LIVE TRANSCRIPTION</span>
          <h2>正在转录</h2>
        </div>
        <n-tag type="warning" size="small">{{ activeTasks.length }} 个任务进行中</n-tag>
      </div>
      <div class="active-task-grid">
        <article v-for="task in activeTasks" :key="task.id" class="active-task-card">
          <div class="active-task-topline">
            <span class="task-number">#{{ task.id }}</span>
            <n-tag type="warning" size="small">{{ stageLabelMap[task.stage] || '处理中' }}</n-tag>
          </div>
          <h3>{{ task.fileName || task.file_name || '未知文件' }}</h3>
          <n-text depth="3" class="active-task-message">{{ task.message || '正在处理' }}</n-text>
          <div class="active-task-duration" aria-live="polite">
            <span>已用时</span>
            <strong>{{ taskDuration(task) }}</strong>
          </div>
          <div class="active-progress-row">
            <n-progress
              type="line"
              :percentage="safeProgress(task.progress)"
              :show-indicator="false"
              processing
            />
            <strong>{{ safeProgress(task.progress) }}%</strong>
          </div>
          <div class="active-task-actions">
            <n-button size="small" type="warning" :disabled="task.pauseRequested || task.cancelRequested" @click="handlePause(task.id)">
              <template #icon><n-icon><PauseOutline /></n-icon></template>
              {{ task.pauseRequested ? '等待暂停' : '暂停' }}
            </n-button>
            <n-button size="small" secondary type="error" :disabled="task.cancelRequested" @click="handleCancel(task.id)">
              <template #icon><n-icon><CloseCircleOutline /></n-icon></template>
              {{ task.cancelRequested ? '正在取消' : '终止' }}
            </n-button>
            <n-button text size="small" @click="router.push(`/tasks/${task.id}`)">查看详情</n-button>
          </div>
        </article>
      </div>
    </section>

    <section v-if="aiActiveTasks.length" class="active-workspace ai-active-workspace">
      <div class="active-workspace-heading">
        <div>
          <span class="section-kicker">LIVE AI ANALYSIS</span>
          <h2>正在分析</h2>
        </div>
        <n-tag type="warning" size="small">{{ aiActiveTasks.length }} 个任务进行中</n-tag>
      </div>
      <div class="active-task-grid">
        <article v-for="task in aiActiveTasks" :key="task.id" class="active-task-card">
          <div class="active-task-topline">
            <span class="task-number">#{{ task.id }}</span>
            <n-tag type="warning" size="small">{{ safeProgress(task.progress) }}%
            </n-tag>
          </div>
          <h3>{{ task.fileName || '未知文件' }}</h3>
          <n-text depth="3" class="active-task-message">{{ task.message || '正在分析' }}</n-text>
          <div class="active-task-duration" aria-live="polite">
            <span>已用时</span>
            <strong>{{ taskDuration(task) }}</strong>
          </div>
        </article>
      </div>
    </section>

    <n-tabs v-model:value="queueTab" type="line" animated>
      <n-tab-pane name="transcription" tab="转录队列">
    <!-- 搜索和过滤 -->
    <n-card size="small">
      <n-space justify="space-between" wrap :size="[12, 12]">
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索文件名 / 路径..."
          style="width: 280px"
          clearable
        >
          <template #prefix>
            <n-icon><SearchOutline /></n-icon>
          </template>
        </n-input>

        <n-radio-group v-model:value="filterStatus" size="small">
          <n-radio-button value="all">全部 ({{ taskStore.tasks.length }})</n-radio-button>
          <n-radio-button value="QUEUED">待处理 ({{ taskStore.taskStats.pending }})</n-radio-button>
          <n-radio-button value="RUNNING">处理中 ({{ taskStore.taskStats.processing }})</n-radio-button>
          <n-radio-button value="PAUSED">已暂停 ({{ taskStore.taskStats.paused }})</n-radio-button>
          <n-radio-button value="SUCCEEDED">已完成 ({{ taskStore.taskStats.completed }})</n-radio-button>
          <n-radio-button value="FAILED">失败 ({{ taskStore.taskStats.failed }})</n-radio-button>
          <n-radio-button value="CANCELED">已取消 ({{ taskStore.taskStats.canceled }})</n-radio-button>
        </n-radio-group>
        <n-space>
          <n-button type="warning" size="small" @click="handlePauseAll">全部暂停</n-button>
          <n-button type="success" size="small" @click="handleStartAll">全部开始</n-button>
        </n-space>
      </n-space>
    </n-card>
      </n-tab-pane>
      <n-tab-pane name="ai" tab="AI 分析队列">
        <n-card>
          <n-empty v-if="!aiTasks.length" description="暂无 AI 分析任务" />
          <n-space justify="end" style="margin-bottom: 12px">
            <n-button type="warning" size="small" @click="handleAiPauseAll">全部暂停</n-button>
            <n-button type="success" size="small" @click="handleAiStartAll">全部开始</n-button>
          </n-space>
          <n-data-table v-if="aiTasks.length" :columns="aiColumns" :data="aiTasks" :loading="aiStore.loading" :pagination="{ pageSize: 20 }" />
        </n-card>
      </n-tab-pane>
    </n-tabs>

    <!-- 任务列表 -->
    <n-card>
      <n-empty v-if="filteredTasks.length === 0" description="暂无任务记录">
        <template #extra>
          <n-button type="primary" @click="$router.push('/sources')">
            前往添加扫描源
          </n-button>
        </template>
      </n-empty>

      <n-data-table
        v-else
        :columns="columns"
        :data="filteredTasks"
        :loading="taskStore.loading"
        :pagination="pagination"
        :single-line="false"
      />
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, computed, h, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NProgress, NIcon, useMessage, useDialog } from 'naive-ui'
import { Refresh as RefreshOutline, Search as SearchOutline, DocumentText as DocumentTextOutline, RefreshCircle as RefreshCircleOutline, CloseCircle as CloseCircleOutline, Trash as TrashOutline, Pause as PauseOutline, Play as PlayOutline } from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'
import { useAiAnalysisStore } from '@/stores/aiAnalysis'
import { formatDateTime, formatElapsed } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const taskStore = useTaskStore()
const aiStore = useAiAnalysisStore()
const queueTab = ref('transcription')

const searchKeyword = ref('')
const filterStatus = ref('all')
const realtimeConnected = ref(false)
const clockNow = ref(Date.now())
let taskSocket = null
let reconnectTimer = null
let clockTimer = null

const pagination = {
  pageSize: 20
}

const filteredTasks = computed(() => {
  let result = taskStore.tasks

  if (filterStatus.value !== 'all') {
    result = result.filter(t => t.status === filterStatus.value)
  }

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(t =>
      (t.file_name || t.fileName || '').toLowerCase().includes(keyword) ||
      (t.path || t.file_path || t.filePath || '').toLowerCase().includes(keyword)
    )
  }

  return result
})

const activeTasks = computed(() => taskStore.tasks.filter(task => task.status === 'RUNNING'))
const aiTasks = computed(() => aiStore.tasks)
const aiActiveTasks = computed(() => aiStore.tasks.filter(task => task.status === 'RUNNING'))

const statusTypeMap = {
  QUEUED: 'default',
  RUNNING: 'warning',
  SUCCEEDED: 'success',
  FAILED: 'error',
  CANCELED: 'default',
  PAUSED: 'warning'
}

const statusLabelMap = {
  QUEUED: '等待处理',
  RUNNING: '处理中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  CANCELED: '已取消',
  PAUSED: '已暂停'
}

const stageLabelMap = {
  QUEUED: '等待处理',
  PROBING: '读取媒体信息',
  EXTRACTING: '提取音频',
  TRANSCRIBING: '语音识别',
  POST_PROCESSING: '整理文案',
  SAVING: '保存结果',
  ANALYZING: 'AI 分析',
  TRANSFERRING: '归档文件',
  COMPLETED: '已完成',
  PAUSED: '已暂停'
}

const columns = [
  {
    title: '任务编号',
    key: 'id',
    width: 100,
    render: (row) => h('span', { style: 'font-family: monospace; font-size: 12px; opacity: 0.7' }, `#${row.id}`)
  },
  {
    title: '素材文件名',
    key: 'file_name',
    ellipsis: { tooltip: true },
    render: (row) => {
      const fileName = row.file_name || row.fileName || '未知文件'
      const filePath = row.path || row.file_path || row.filePath || ''
      return h('div', [
        h('div', { style: 'font-weight: 600; margin-bottom: 4px' }, fileName),
        h('div', { style: 'font-size: 11px; opacity: 0.6; word-break: break-all' }, filePath)
      ])
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => h(NTag, {
      type: statusTypeMap[row.status] || 'default',
      size: 'small'
    }, {
      default: () => statusLabelMap[row.status] || row.status
    })
  },
  {
    title: '当前阶段',
    key: 'stage',
    width: 130,
    render: (row) => h(NTag, { type: row.status === 'RUNNING' ? 'warning' : 'default', size: 'small' }, {
      default: () => stageLabelMap[row.stage] || row.stage || '--'
    })
  },
  {
    title: '总进度',
    key: 'progress',
    width: 130,
    render: (row) => h('div', { class: 'table-progress' }, [
      h(NProgress, {
        type: 'line',
        percentage: safeProgress(row.progress),
        status: row.status === 'FAILED' ? 'error' : (row.status === 'SUCCEEDED' ? 'success' : 'default'),
        showIndicator: false
      }),
      h('span', `${safeProgress(row.progress)}%`)
    ])
  },
  {
    title: '总耗时',
    key: 'duration',
    width: 120,
    render: (row) => h('span', { class: 'duration-value' }, taskDuration(row))
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 160,
    render: (row) => formatDateTime(row.updated_at || row.updatedAt)
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right',
    render: (row) => {
      const actions = []

      actions.push(
        h(NButton, {
          text: true,
          type: 'primary',
          size: 'small',
          onClick: () => router.push(`/tasks/${row.id}`)
        }, {
          default: () => '查看详情',
          icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) })
        })
      )

      if (row.status === 'QUEUED' || row.status === 'RUNNING') {
        actions.push(
          h(NButton, {
            text: true,
            type: 'warning',
            size: 'small',
            onClick: () => handlePause(row.id)
          }, {
            default: () => row.pauseRequested ? '等待暂停' : '暂停',
            icon: () => h(NIcon, null, { default: () => h(PauseOutline) })
          })
        )
        actions.push(
          h(NButton, {
            text: true,
            type: 'error',
            size: 'small',
            disabled: row.cancelRequested,
            onClick: () => handleCancel(row.id)
          }, {
            default: () => row.cancelRequested ? '正在取消' : '终止',
            icon: () => h(NIcon, null, { default: () => h(CloseCircleOutline) })
          })
        )
      }

      if (row.status === 'PAUSED') {
        actions.push(
          h(NButton, {
            text: true,
            type: 'success',
            size: 'small',
            onClick: () => handleResume(row.id)
          }, {
            default: () => '恢复',
            icon: () => h(NIcon, null, { default: () => h(PlayOutline) })
          })
        )
      }

      if (row.status === 'FAILED') {
        actions.push(
          h(NButton, {
            text: true,
            type: 'success',
            size: 'small',
            onClick: () => handleRetry(row.id)
          }, {
            default: () => '重试',
            icon: () => h(NIcon, null, { default: () => h(RefreshCircleOutline) })
          })
        )
      }

      if (row.status === 'FAILED' || row.status === 'CANCELED' || row.status === 'PAUSED' || row.status === 'SUCCEEDED') {
        actions.push(
          h(NButton, {
            text: true,
            type: 'error',
            size: 'small',
            onClick: () => handleDelete(row.id)
          }, {
            default: () => '删除',
            icon: () => h(NIcon, null, { default: () => h(TrashOutline) })
          })
        )
      }

      return h('div', { style: 'display: flex; gap: 8px; flex-wrap: wrap' }, actions)
    }
  }
]

const aiColumns = [
  { title: '任务编号', key: 'id', width: 100 },
  { title: '素材文件', key: 'fileName', ellipsis: { tooltip: true } },
  { title: '分析类型', key: 'analysisType', width: 130, render: row => ({ FULL: '摘要和总结', SUMMARY: '摘要', CONCLUSION: '总结', OUTLINE: '总结', KEY_POINTS: '总结', QUOTES: '总结' }[row.analysisType] || row.analysisType) },
  { title: '状态', key: 'status', width: 100, render: row => h(NTag, { type: row.status === 'SUCCEEDED' ? 'success' : row.status === 'FAILED' ? 'error' : 'warning', size: 'small' }, { default: () => ({ QUEUED: '等待处理', RUNNING: '分析中', SUCCEEDED: '已完成', FAILED: '失败', CANCELED: '已取消' }[row.status] || row.status) }) },
  { title: '阶段进度', key: 'progress', width: 130, render: row => h('span', `${safeProgress(row.progress)}%`) },
  { title: '总耗时', key: 'duration', width: 120, render: row => h('span', { class: 'duration-value' }, taskDuration(row)) },
  { title: '提示', key: 'message', ellipsis: { tooltip: true } },
  {
    title: '操作', key: 'actions', width: 220,
    render: row => {
      const actions = []
      if (row.status === 'QUEUED' || row.status === 'RUNNING') actions.push(h(NButton, { text: true, size: 'small', type: 'warning', onClick: () => aiStore.pauseTask(row.id) }, { default: () => row.status === 'RUNNING' ? '暂停' : '暂停' }))
      if (row.status === 'PAUSED' || row.status === 'FAILED' || row.status === 'CANCELED') actions.push(h(NButton, { text: true, size: 'small', type: 'success', onClick: () => aiStore.startTask(row.id) }, { default: () => row.status === 'PAUSED' ? '继续' : '开始' }))
      if (row.status === 'QUEUED' || row.status === 'RUNNING' || row.status === 'PAUSED') actions.push(h(NButton, { text: true, size: 'small', type: 'error', onClick: () => aiStore.cancelTask(row.id) }, { default: () => '取消' }))
      return h('div', { style: 'display:flex;gap:8px;flex-wrap:wrap' }, actions)
    }
  }
]

function safeProgress(value) {
  return Math.max(0, Math.min(100, Number(value) || 0))
}

function taskDuration(task) {
  const startedAt = task.startedAt || task.started_at
  const finishedAt = task.finishedAt || task.finished_at
  const stoppedAt = task.status === 'PAUSED' ? (task.updatedAt || task.updated_at) : undefined
  return formatElapsed(startedAt, finishedAt || stoppedAt, clockNow.value)
}

function connectRealtime() {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (taskSocket) {
    taskSocket.onclose = null
    taskSocket.close()
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  taskSocket = new WebSocket(`${protocol}//${window.location.host}/ws/tasks`)
  taskSocket.onopen = () => {
    realtimeConnected.value = true
  }
  taskSocket.onmessage = event => {
    try {
      const payload = JSON.parse(event.data)
      if (payload.type === 'task.snapshot') {
        taskStore.replaceRealtimeTasks(payload.tasks || [])
      } else if (payload.type === 'task.updated' || payload.type === 'task.completed' || payload.type === 'task.failed') {
        taskStore.mergeRealtimeTask(payload)
      } else if (payload.type === 'ai.task.updated' || payload.type === 'ai.task.completed' || payload.type === 'ai.task.failed') {
        aiStore.mergeRealtimeTask(payload)
      } else if (payload.type === 'ai.task.deleted') {
        aiStore.removeRealtimeTask(payload.taskId)
      } else if (payload.type === 'task.created') {
        taskStore.fetchTasks()
      } else if (payload.type === 'task.deleted') {
        taskStore.removeRealtimeTask(payload.taskId)
      }
    } catch (error) {
      console.warn('任务实时消息解析失败', error)
    }
  }
  taskSocket.onerror = () => {
    realtimeConnected.value = false
  }
  taskSocket.onclose = () => {
    realtimeConnected.value = false
    if (!reconnectTimer) {
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        connectRealtime()
      }, 3000)
    }
  }
}

async function handlePauseAll() {
  try {
    const result = await taskStore.pauseAllTasks()
    message.info(`已请求暂停 ${result.updated || 0} 个转录任务`)
  } catch (error) {
    message.error('全部暂停失败')
  }
}

async function handleStartAll() {
  try {
    const result = await taskStore.startAllTasks()
    message.success(`已恢复 ${result.updated || 0} 个转录任务`)
  } catch (error) {
    message.error('全部开始失败')
  }
}

async function handleAiPauseAll() {
  try {
    const result = await aiStore.pauseAllTasks()
    message.info(`已请求暂停 ${result.updated || 0} 个 AI 任务`)
  } catch (error) {
    message.error('AI 全部暂停失败')
  }
}

async function handleAiStartAll() {
  try {
    const result = await aiStore.startAllTasks()
    message.success(`已恢复 ${result.updated || 0} 个 AI 任务`)
  } catch (error) {
    message.error('AI 全部开始失败')
  }
}

async function handleRetry(id) {
  try {
    await taskStore.retryTask(id)
    message.success('任务已重新加入队列')
  } catch (error) {
    message.error('重试失败')
  }
}

async function handlePause(id) {
  try {
    await taskStore.pauseTask(id)
    message.info('任务已请求暂停')
  } catch (error) {
    message.error('暂停失败，请稍后重试')
  }
}

async function handleResume(id) {
  try {
    await taskStore.resumeTask(id)
    message.success('任务已恢复处理')
  } catch (error) {
    message.error('恢复失败，请稍后重试')
  }
}

function handleCancel(id) {
  dialog.warning({
    title: '取消任务',
    content: '确定要强制中断并取消该任务吗？',
    positiveText: '确认取消',
    negativeText: '继续执行',
    onPositiveClick: async () => {
      try {
        await taskStore.cancelTask(id)
        message.info('任务已取消')
      } catch (error) {
        message.error('取消失败')
      }
    }
  })
}

function handleDelete(id) {
  dialog.warning({
    title: '删除记录',
    content: '确定从任务列表中清理该记录？',
    positiveText: '删除',
    negativeText: '保留',
    onPositiveClick: async () => {
      try {
        await taskStore.deleteTask(id)
        message.success('记录已清理')
      } catch (error) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  clockTimer = window.setInterval(() => { clockNow.value = Date.now() }, 1000)
  taskStore.fetchTasks()
  aiStore.fetchTasks()
  connectRealtime()
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
  if (reconnectTimer) window.clearTimeout(reconnectTimer)
  if (taskSocket) {
    taskSocket.onclose = null
    taskSocket.close()
  }
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 4px;
}

.realtime-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 5px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.55;
}

.realtime-dot.connected {
  opacity: 1;
  box-shadow: 0 0 0 3px rgba(24, 160, 88, 0.14);
}

.active-workspace {
  padding: 20px;
  border: 1px solid rgba(240, 160, 32, 0.35);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(240, 160, 32, 0.1), rgba(24, 160, 88, 0.04));
}

.active-workspace-heading,
.active-task-topline,
.active-progress-row,
.active-task-actions {
  display: flex;
  align-items: center;
}

.active-workspace-heading {
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-kicker {
  color: #a16b00;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.active-workspace-heading h2 {
  margin: 3px 0 0;
  font-size: 20px;
}

.active-task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
}

.active-task-card {
  padding: 18px;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  background: var(--n-color-card);
  box-shadow: 0 8px 24px rgba(30, 38, 30, 0.08);
}

.active-task-topline {
  justify-content: space-between;
  gap: 12px;
}

.task-number {
  color: var(--n-text-color-3);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
}

.active-task-card h3 {
  margin: 15px 0 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 17px;
}

.active-task-message {
  display: block;
  min-height: 20px;
  font-size: 12px;
}

.active-task-duration {
  display: flex;
  align-items: baseline;
  gap: 9px;
  margin-top: 11px;
  color: var(--n-text-color-3);
  font-size: 12px;
}

.active-task-duration strong,
.duration-value {
  color: var(--n-text-color);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

.active-progress-row {
  gap: 12px;
  margin-top: 17px;
}

.active-progress-row .n-progress {
  flex: 1;
}

.active-progress-row strong {
  min-width: 42px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.active-task-actions {
  gap: 8px;
  margin-top: 18px;
}

.active-task-actions .n-button:last-child {
  margin-left: auto;
}

.table-progress {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 140px;
}

.table-progress .n-progress {
  flex: 1;
}

.table-progress > span {
  width: 38px;
  text-align: right;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 720px) {
  .active-workspace { padding: 15px; }
  .active-workspace-heading { align-items: flex-start; flex-direction: column; }
}
</style>
