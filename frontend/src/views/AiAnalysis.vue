<template>
  <n-space vertical :size="20">
    <div class="page-header">
      <div><h1 class="page-title">AI 分析队列</h1><n-text depth="3">独立管理摘要、提纲、核心观点和金句生成任务</n-text></div>
      <n-button :loading="store.loading" @click="() => store.fetchTasks()"><template #icon><n-icon><RefreshOutline /></n-icon></template>刷新队列</n-button>
    </div>
    <n-space wrap><n-tag>待处理 {{ store.stats.queued }}</n-tag><n-tag type="warning">分析中 {{ store.stats.running }}</n-tag><n-tag type="success">已完成 {{ store.stats.succeeded }}</n-tag><n-tag type="error">失败 {{ store.stats.failed }}</n-tag></n-space>
    <n-card><n-empty v-if="!store.tasks.length" description="暂无 AI 分析任务" /><n-data-table v-else :columns="columns" :data="store.tasks" :loading="store.loading" :pagination="{ pageSize: 20 }" /></n-card>
  </n-space>
</template>

<script setup>
import { h, onMounted } from 'vue'
import { NButton, NTag, NIcon } from 'naive-ui'
import { Refresh as RefreshOutline } from '@vicons/ionicons5'
import { useAiAnalysisStore } from '@/stores/aiAnalysis'
const store = useAiAnalysisStore()
const typeLabels = { SUMMARY: '摘要', OUTLINE: '内容提纲', KEY_POINTS: '核心观点', QUOTES: '金句' }
const statusLabels = { QUEUED: '待处理', RUNNING: '分析中', PAUSED: '已暂停', SUCCEEDED: '已完成', FAILED: '失败', CANCELED: '已取消' }
const columns = [
  { title: '任务', key: 'id', width: 80, render: row => `#${row.id}` },
  { title: '素材文件', key: 'fileName', ellipsis: { tooltip: true } },
  { title: '分析类型', key: 'analysisType', width: 120, render: row => typeLabels[row.analysisType] || row.analysisType },
  { title: '状态', key: 'status', width: 100, render: row => h(NTag, { type: row.status === 'SUCCEEDED' ? 'success' : row.status === 'FAILED' ? 'error' : row.status === 'PAUSED' ? 'default' : 'warning', size: 'small' }, { default: () => statusLabels[row.status] || row.status }) },
  { title: '进度', key: 'progress', width: 80, render: row => `${row.progress || 0}%` },
  { title: '提示', key: 'message', ellipsis: { tooltip: true } },
  { title: '操作', key: 'actions', width: 230, render: row => {
    const actions = []
    if (row.status === 'QUEUED' || row.status === 'RUNNING') actions.push(h(NButton, { text: true, size: 'small', onClick: () => store.pauseTask(row.id) }, { default: () => '暂停' }))
    if (row.status === 'PAUSED' || row.status === 'FAILED' || row.status === 'CANCELED') actions.push(h(NButton, { text: true, type: 'success', size: 'small', onClick: () => store.startTask(row.id) }, { default: () => row.status === 'PAUSED' ? '继续' : '开始' }))
    if (row.status === 'QUEUED' || row.status === 'RUNNING' || row.status === 'PAUSED') actions.push(h(NButton, { text: true, type: 'error', size: 'small', onClick: () => store.cancelTask(row.id) }, { default: () => '取消' }))
    return h('div', { style: 'display:flex;gap:8px;flex-wrap:wrap' }, actions)
  }}
]
onMounted(() => store.fetchTasks())
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
.page-title { margin: 0 0 4px; font-size: 24px; font-weight: 600; }
</style>
