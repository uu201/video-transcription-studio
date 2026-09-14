<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">AI 分析队列</h1>
        <n-text depth="3">独立管理摘要和总结生成任务</n-text>
      </div>
      <n-space align="center">
        <n-tag :type="realtimeConnected ? 'success' : 'warning'" size="small" round>
          <span class="realtime-dot" :class="{ connected: realtimeConnected }"></span>
          {{ realtimeConnected ? '实时连接' : '正在重连' }}
        </n-tag>
        <n-button :loading="store.loading" @click="store.fetchTasks()">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新队列
        </n-button>
      </n-space>
    </div>

    <section v-if="activeTasks.length" class="active-workspace">
      <div class="active-workspace-heading">
        <div>
          <span class="section-kicker">LIVE AI ANALYSIS</span>
          <h2>正在分析</h2>
        </div>
        <n-tag type="warning" size="small">{{ activeTasks.length }} 个任务进行中</n-tag>
      </div>
      <div class="active-task-grid">
        <article v-for="task in activeTasks" :key="task.id" class="active-task-card">
          <div class="active-task-topline">
            <span class="task-number">#{{ task.id }}</span>
            <n-tag type="warning" size="small">分析中</n-tag>
          </div>
          <h3>{{ task.fileName || '未知文件' }}</h3>
          <n-text depth="3" class="active-task-message">{{ task.message || '正在分析' }}</n-text>
          <div class="active-task-duration" aria-live="polite">
            <span>已用时</span>
            <strong>{{ taskDuration(task) }}</strong>
          </div>
          <div class="active-progress-row">
            <n-progress type="line" :percentage="safeProgress(task.progress)" :show-indicator="false" processing />
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
            <n-button text size="small" @click="router.push(`/tasks/${task.transcriptionTaskId}`)">查看详情</n-button>
          </div>
        </article>
      </div>
    </section>

    <n-space wrap>
      <n-tag>待处理 {{ store.stats.queued }}</n-tag>
      <n-tag type="warning">分析中 {{ store.stats.running }}</n-tag>
      <n-tag type="warning">已暂停 {{ store.stats.paused }}</n-tag>
      <n-tag type="success">已完成 {{ store.stats.succeeded }}</n-tag>
      <n-tag type="error">失败 {{ store.stats.failed }}</n-tag>
      <n-tag>已取消 {{ store.stats.canceled }}</n-tag>
    </n-space>

    <n-card size="small">
      <n-space justify="space-between" wrap :size="[12, 12]">
        <n-input v-model:value="searchKeyword" placeholder="搜索文件名..." style="width: 280px" clearable />
        <n-radio-group v-model:value="filterStatus" size="small">
          <n-radio-button value="all">全部 ({{ store.tasks.length }})</n-radio-button>
          <n-radio-button value="QUEUED">待处理 ({{ store.stats.queued }})</n-radio-button>
          <n-radio-button value="RUNNING">分析中 ({{ store.stats.running }})</n-radio-button>
          <n-radio-button value="PAUSED">已暂停 ({{ store.stats.paused }})</n-radio-button>
          <n-radio-button value="SUCCEEDED">已完成 ({{ store.stats.succeeded }})</n-radio-button>
          <n-radio-button value="FAILED">失败 ({{ store.stats.failed }})</n-radio-button>
          <n-radio-button value="CANCELED">已取消 ({{ store.stats.canceled }})</n-radio-button>
        </n-radio-group>
        <n-space>
          <n-button type="warning" size="small" @click="handlePauseAll">全部暂停</n-button>
          <n-button type="success" size="small" @click="handleStartAll">全部开始</n-button>
        </n-space>
      </n-space>
    </n-card>

    <n-card>
      <n-empty v-if="!filteredTasks.length" description="暂无 AI 分析任务" />
      <n-data-table v-else :columns="columns" :data="filteredTasks" :loading="store.loading" :pagination="{ pageSize: 20 }" :single-line="false" />
    </n-card>
  </n-space>
</template>

<script setup>
import { h, ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NProgress, NIcon, useMessage, useDialog } from 'naive-ui'
import {
  Refresh as RefreshOutline,
  DocumentText as DocumentTextOutline,
  CloseCircle as CloseCircleOutline,
  Pause as PauseOutline,
  Play as PlayOutline,
  RefreshCircle as RefreshCircleOutline,
  Trash as TrashOutline
} from '@vicons/ionicons5'
import { useAiAnalysisStore } from '@/stores/aiAnalysis'
import { formatElapsed } from '@/utils/format'

const store = useAiAnalysisStore()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const searchKeyword = ref('')
const filterStatus = ref('all')
const realtimeConnected = ref(false)
const clockNow = ref(Date.now())
let aiSocket = null
let reconnectTimer = null
let clockTimer = null

const typeLabels = { FULL: '摘要和总结', SUMMARY: '摘要', CONCLUSION: '总结', OUTLINE: '总结', KEY_POINTS: '总结', QUOTES: '总结' }
const statusLabels = { QUEUED: '待处理', RUNNING: '分析中', PAUSED: '已暂停', SUCCEEDED: '已完成', FAILED: '失败', CANCELED: '已取消' }
const statusTypeMap = { QUEUED: 'default', RUNNING: 'warning', PAUSED: 'warning', SUCCEEDED: 'success', FAILED: 'error', CANCELED: 'default' }

const filteredTasks = computed(() => {
  let result = store.tasks
  if (filterStatus.value !== 'all') result = result.filter(task => task.status === filterStatus.value)
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(task => (task.fileName || '').toLowerCase().includes(keyword))
  }
  return result
})

const activeTasks = computed(() => store.tasks.filter(task => task.status === 'RUNNING'))

const columns = [
  { title: '任务编号', key: 'id', width: 100, render: row => h('span', { style: 'font-family: monospace; font-size: 12px; opacity: 0.7' }, `#${row.id}`) },
  { title: '素材文件', key: 'fileName', ellipsis: { tooltip: true } },
  { title: '分析类型', key: 'analysisType', width: 130, render: row => typeLabels[row.analysisType] || row.analysisType },
  { title: '状态', key: 'status', width: 100, render: row => h(NTag, { type: statusTypeMap[row.status] || 'default', size: 'small' }, { default: () => statusLabels[row.status] || row.status }) },
  {
    title: '阶段进度', key: 'progress', width: 140,
    render: row => h('div', { class: 'table-progress' }, [
      h(NProgress, { type: 'line', percentage: safeProgress(row.progress), status: row.status === 'FAILED' ? 'error' : row.status === 'SUCCEEDED' ? 'success' : 'default', showIndicator: false }),
      h('span', `${safeProgress(row.progress)}%`)
    ])
  },
  { title: '总耗时', key: 'duration', width: 120, render: row => h('span', { class: 'duration-value' }, taskDuration(row)) },
  { title: '提示', key: 'message', ellipsis: { tooltip: true } },
  { title: '更新时间', key: 'updatedAt', width: 170, render: row => formatDateTime(row.updatedAt || row.createdAt) },
  {
    title: '操作', key: 'actions', width: 290, fixed: 'right', render: row => {
      const actions = [h(NButton, { text: true, type: 'primary', size: 'small', onClick: () => router.push(`/tasks/${row.transcriptionTaskId}`) }, { default: () => '查看详情', icon: () => h(NIcon, null, { default: () => h(DocumentTextOutline) }) })]
      if (row.status === 'QUEUED' || row.status === 'RUNNING') {
        actions.push(h(NButton, { text: true, type: 'warning', size: 'small', disabled: row.pauseRequested || row.cancelRequested, onClick: () => handlePause(row.id) }, { default: () => row.pauseRequested ? '等待暂停' : '暂停', icon: () => h(NIcon, null, { default: () => h(PauseOutline) }) }))
      }
      if (row.status === 'PAUSED') actions.push(h(NButton, { text: true, type: 'success', size: 'small', onClick: () => handleStart(row.id) }, { default: () => '恢复', icon: () => h(NIcon, null, { default: () => h(PlayOutline) }) }))
      if (row.status === 'QUEUED' || row.status === 'RUNNING' || row.status === 'PAUSED') actions.push(h(NButton, { text: true, type: 'error', size: 'small', disabled: row.cancelRequested, onClick: () => handleCancel(row.id) }, { default: () => row.cancelRequested ? '正在取消' : '终止', icon: () => h(NIcon, null, { default: () => h(CloseCircleOutline) }) }))
      if (row.status === 'FAILED' || row.status === 'CANCELED') actions.push(h(NButton, { text: true, type: 'success', size: 'small', onClick: () => handleRetry(row.id) }, { default: () => '重试', icon: () => h(NIcon, null, { default: () => h(RefreshCircleOutline) }) }))
      if (row.status === 'SUCCEEDED' || row.status === 'FAILED' || row.status === 'CANCELED') actions.push(h(NButton, { text: true, type: 'error', size: 'small', onClick: () => handleDelete(row.id) }, { default: () => '删除', icon: () => h(NIcon, null, { default: () => h(TrashOutline) }) }))
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

function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

async function handlePauseAll() {
  try {
    const result = await store.pauseAllTasks()
    message.info(`已暂停 ${result.updated || 0} 个 AI 分析任务`)
  } catch (error) {
    message.error(error?.response?.data?.detail || '全部暂停失败')
  }
}

async function handleStartAll() {
  try {
    const result = await store.startAllTasks()
    message.success(`已恢复 ${result.updated || 0} 个 AI 分析任务`)
  } catch (error) {
    message.error(error?.response?.data?.detail || '全部开始失败')
  }
}

function connectRealtime() {
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (aiSocket) {
    aiSocket.onclose = null
    aiSocket.close()
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  aiSocket = new WebSocket(`${protocol}//${window.location.host}/ws/tasks`)
  aiSocket.onopen = () => { realtimeConnected.value = true }
  aiSocket.onmessage = event => {
    try {
      const payload = JSON.parse(event.data)
      if (payload.type === 'ai.task.created' || payload.type === 'ai.task.updated' || payload.type === 'ai.task.completed' || payload.type === 'ai.task.failed') {
        store.mergeRealtimeTask(payload)
      } else if (payload.type === 'ai.task.deleted') {
        store.removeRealtimeTask(payload.taskId)
      }
    } catch (error) {
      console.warn('AI 任务实时消息解析失败', error)
    }
  }
  aiSocket.onerror = () => { realtimeConnected.value = false }
  aiSocket.onclose = () => {
    realtimeConnected.value = false
    if (!reconnectTimer) reconnectTimer = window.setTimeout(() => { reconnectTimer = null; connectRealtime() }, 3000)
  }
}

async function handlePause(id) {
  try { await store.pauseTask(id); message.info('AI 分析已请求暂停') } catch (error) { message.error(error?.response?.data?.detail || '暂停失败，请稍后重试') }
}

async function handleStart(id) {
  try { await store.startTask(id); message.success('AI 分析已恢复') } catch (error) { message.error(error?.response?.data?.detail || '恢复失败，请稍后重试') }
}

async function handleRetry(id) {
  try { await store.retryTask(id); message.success('AI 分析已重新加入队列') } catch (error) { message.error(error?.response?.data?.detail || '重试失败，请稍后重试') }
}

function handleCancel(id) {
  dialog.warning({
    title: '取消 AI 分析', content: '确定要取消该 AI 分析任务吗？', positiveText: '确认取消', negativeText: '继续执行',
    onPositiveClick: async () => {
      try { await store.cancelTask(id); message.info('AI 分析已取消') } catch (error) { message.error(error?.response?.data?.detail || '取消失败') }
    }
  })
}

function handleDelete(id) {
  dialog.warning({
    title: '删除记录', content: '确定从 AI 分析队列中清理该记录？', positiveText: '删除', negativeText: '保留',
    onPositiveClick: async () => {
      try { await store.deleteTask(id); message.success('记录已清理') } catch (error) { message.error(error?.response?.data?.detail || '删除失败') }
    }
  })
}

onMounted(() => {
  clockTimer = window.setInterval(() => { clockNow.value = Date.now() }, 1000)
  store.fetchTasks()
  connectRealtime()
})

onUnmounted(() => {
  if (clockTimer) window.clearInterval(clockTimer)
  if (reconnectTimer) window.clearTimeout(reconnectTimer)
  if (aiSocket) {
    aiSocket.onclose = null
    aiSocket.close()
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.page-title { margin: 0 0 4px; font-size: 24px; font-weight: 600; }
.realtime-dot { display: inline-block; width: 7px; height: 7px; margin-right: 5px; border-radius: 50%; background: currentColor; opacity: 0.55; }
.realtime-dot.connected { opacity: 1; box-shadow: 0 0 0 3px rgba(24, 160, 88, 0.14); }
.active-workspace { padding: 20px; border: 1px solid rgba(240, 160, 32, 0.35); border-radius: 10px; background: linear-gradient(135deg, rgba(240, 160, 32, 0.1), rgba(24, 160, 88, 0.04)); }
.active-workspace-heading, .active-task-topline, .active-progress-row, .active-task-actions { display: flex; align-items: center; }
.active-workspace-heading { justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.section-kicker { color: #a16b00; font-size: 11px; font-weight: 700; letter-spacing: 0.12em; }
.active-workspace-heading h2 { margin: 3px 0 0; font-size: 20px; }
.active-task-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
.active-task-card { padding: 18px; border: 1px solid var(--n-border-color); border-radius: 8px; background: var(--n-color-card); box-shadow: 0 8px 24px rgba(30, 38, 30, 0.08); }
.active-task-topline { justify-content: space-between; gap: 12px; }
.task-number { color: var(--n-text-color-3); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
.active-task-card h3 { margin: 15px 0 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 17px; }
.active-task-message { display: block; min-height: 20px; font-size: 12px; }
.active-task-duration { display: flex; align-items: baseline; gap: 9px; margin-top: 11px; color: var(--n-text-color-3); font-size: 12px; }
.active-task-duration strong, .duration-value { color: var(--n-text-color); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }
.active-progress-row { gap: 12px; margin-top: 17px; }
.active-progress-row .n-progress { flex: 1; }
.active-progress-row strong { min-width: 42px; text-align: right; font-variant-numeric: tabular-nums; }
.active-task-actions { gap: 8px; margin-top: 18px; }
.active-task-actions .n-button:last-child { margin-left: auto; }
.table-progress { display: flex; align-items: center; gap: 9px; min-width: 140px; }
.table-progress .n-progress { flex: 1; }
.table-progress > span { width: 38px; text-align: right; font-size: 12px; font-variant-numeric: tabular-nums; }
@media (max-width: 720px) { .active-workspace { padding: 15px; } .active-workspace-heading { align-items: flex-start; flex-direction: column; } }
</style>
