<template>
  <n-spin :show="loading">
    <n-space vertical :size="24" v-if="task">
      <div class="page-header">
        <div>
          <n-button text @click="router.push('/tasks')" style="margin-bottom: 8px">
            <template #icon>
              <n-icon><ArrowBackOutline /></n-icon>
            </template>
            返回任务列表
          </n-button>
          <h1 class="page-title">#{{ task.id }} - {{ task.fileName || '未命名媒体' }}</h1>
          <n-text depth="3" style="word-break: break-all">{{ task.path || '未记录文件路径' }}</n-text>
        </div>
        <n-space>
          <n-button v-if="task.status === 'FAILED'" type="warning" @click="handleRetry">
            <template #icon>
              <n-icon><RefreshCircleOutline /></n-icon>
            </template>
            重新尝试
          </n-button>
          <n-button v-if="task.status === 'RUNNING'" type="error" @click="handleCancel">
            <template #icon>
              <n-icon><CloseCircleOutline /></n-icon>
            </template>
            终止任务
          </n-button>
          <n-button v-if="task.status === 'SUCCEEDED'" type="success" disabled>
            <template #icon>
              <n-icon><CheckmarkCircleOutline /></n-icon>
            </template>
            任务已完成
          </n-button>
        </n-space>
      </div>

      <!-- 基础信息卡片 -->
      <n-grid :cols="4" :x-gap="16" responsive="screen">
        <n-gi>
          <n-card size="small">
            <n-statistic label="媒体时长" :value="formatDuration(mediaInfo.duration)" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              大小: {{ formatBytes(task.fileSize) }}
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="分辨率" :value="formatResolution(mediaInfo)" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              格式: {{ mediaInfo.formatName || task.extension || 'N/A' }}
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="当前状态">
              <template #default>
                <n-tag :type="statusTypeMap[task.status]" size="medium">
                  {{ statusLabelMap[task.status] }}
                </n-tag>
              </template>
            </n-statistic>
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              阶段: {{ stageLabelMap[task.stage] || task.stage || '--' }}
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="总体进度" :value="`${task.progress || 0}%`" />
            <n-progress
              type="line"
              :percentage="task.progress || 0"
              :status="task.status === 'FAILED' ? 'error' : (task.status === 'SUCCEEDED' ? 'success' : 'default')"
              :show-indicator="false"
              style="margin-top: 8px"
            />
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 错误信息 -->
      <n-alert v-if="task.status === 'FAILED' && (task.error?.message || task.message)" type="error" title="任务执行中断">
        {{ task.error?.message || task.message }}
      </n-alert>

      <!-- 转写结果 -->
      <n-card v-if="task.status === 'SUCCEEDED'" title="转写文案资产">
        <template #header-extra>
          <n-space>
            <n-button size="small" @click="handleExport('txt')">
              <template #icon>
                <n-icon><DocumentOutline /></n-icon>
              </template>
              导出 TXT
            </n-button>
            <n-button size="small" @click="handleExport('json')">
              <template #icon>
                <n-icon><CodeOutline /></n-icon>
              </template>
              导出 JSON
            </n-button>
            <n-button size="small" @click="handleExport('srt')">
              <template #icon>
                <n-icon><FilmOutline /></n-icon>
              </template>
              导出 SRT
            </n-button>
          </n-space>
        </template>

        <n-tabs type="line" v-model:value="activeTab">
          <n-tab-pane name="clean" tab="清洗后文案 (推荐)">
            <div v-if="cleanText" class="transcript-box">{{ cleanText }}</div>
            <n-empty v-else description="识别已完成，但没有可显示的清洗文案">
              <template #extra>
                <n-text depth="3">可以切换到“完整 JSON”检查原始识别结果。</n-text>
              </template>
            </n-empty>
          </n-tab-pane>
          <n-tab-pane name="raw" tab="原始识别文本">
            <div v-if="rawText" class="transcript-box">{{ rawText }}</div>
            <n-empty v-else description="没有原始文本可显示" />
          </n-tab-pane>
          <n-tab-pane name="json" tab="完整 JSON">
            <div v-if="transcript" class="transcript-box json-box">
              {{ JSON.stringify(transcript, null, 2) }}
            </div>
            <n-empty v-else description="转写结果记录不存在" />
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- 时间轴分段 -->
      <n-card v-if="segments.length > 0" title="时间戳句子分段">
        <template #header-extra>
          <n-text depth="3">共 {{ segments.length }} 段</n-text>
        </template>

        <n-data-table
          :columns="segmentColumns"
          :data="segments"
          :pagination="{ pageSize: 10 }"
          size="small"
        />
      </n-card>

      <!-- 处理流程时间线 -->
      <n-card title="处理全流程时间线">
        <n-timeline v-if="pipeline.length > 0">
          <n-timeline-item
            v-for="(step, idx) in pipeline"
            :key="`${step.createdAt}-${idx}`"
            :type="step.type"
            :title="step.title"
            :content="step.content"
            :time="formatDateTime(step.createdAt)"
          />
        </n-timeline>
        <n-empty v-else description="暂无处理事件记录" />
      </n-card>
    </n-space>
  </n-spin>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import {
  ArrowBack as ArrowBackOutline,
  RefreshCircle as RefreshCircleOutline,
  CloseCircle as CloseCircleOutline,
  CheckmarkCircle as CheckmarkCircleOutline,
  Document as DocumentOutline,
  Code as CodeOutline,
  Film as FilmOutline
} from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'
import api from '@/api'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const taskStore = useTaskStore()

const loading = ref(false)
const task = ref(null)
const activeTab = ref('clean')

const mediaInfo = computed(() => {
  const raw = task.value?.mediaInfo || {}
  return {
    duration: raw.duration,
    width: raw.width,
    height: raw.height,
    formatName: raw.formatName || raw.format_name
  }
})
const transcript = computed(() => task.value?.transcript || null)
const cleanText = computed(() => transcript.value?.cleanText?.trim() || '')
const rawText = computed(() => transcript.value?.rawText?.trim() || '')
const segments = computed(() => task.value?.segments || [])
const pipeline = computed(() => (task.value?.events || []).map(event => ({
  type: event.level === 'ERROR' ? 'error' : (event.level === 'SUCCESS' ? 'success' : 'default'),
  title: event.message || event.stage || '处理事件',
  content: event.detail || event.stage || '',
  createdAt: event.createdAt
})))

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

const segmentColumns = [
  { title: '#', key: 'sequence', width: 50 },
  {
    title: '时间区间',
    key: 'time',
    width: 180,
    render: (row) => `${row.start} → ${row.end}`
  },
  {
    title: '说话人',
    key: 'speaker',
    width: 100
  },
  {
    title: '分段文案',
    key: 'text',
    ellipsis: { tooltip: true }
  },
  {
    title: '置信度',
    key: 'confidence',
    width: 90,
    render: (row) => Number.isFinite(Number(row.confidence)) ? `${(Number(row.confidence) * 100).toFixed(0)}%` : '—'
  }
]

function formatDuration(value) {
  const seconds = Number(value)
  if (!Number.isFinite(seconds) || seconds <= 0) return '--'
  const minutes = Math.floor(seconds / 60)
  const remaining = Math.round(seconds % 60)
  return minutes > 0 ? `${minutes} 分 ${String(remaining).padStart(2, '0')} 秒` : `${remaining} 秒`
}

function formatBytes(value) {
  const bytes = Number(value)
  if (!Number.isFinite(bytes) || bytes < 0) return '--'
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`
}

function formatResolution(info) {
  return info.width && info.height ? `${info.width} × ${info.height}` : '仅音频'
}

function formatDateTime(value) {
  if (!value) return '--'
  return String(value).replace('T', ' ').replace('Z', '')
}

async function loadTask() {
  loading.value = true
  try {
    const id = route.params.id
    const detail = await taskStore.getTaskDetail(id)
    if (!detail) throw new Error('任务详情不存在')
    const [transcriptResult, segmentsResult] = await Promise.all([
      api.getTranscript(id).catch(() => null),
      api.getTaskSegments(id).catch(() => [])
    ])
    task.value = { ...detail, transcript: transcriptResult, segments: segmentsResult }
  } catch (error) {
    message.error('加载任务详情失败')
    router.push('/tasks')
  } finally {
    loading.value = false
  }
}

async function handleRetry() {
  try {
    await taskStore.retryTask(task.value.id)
    message.success('任务已重新加入队列')
    await loadTask()
  } catch (error) {
    message.error('重试失败')
  }
}

function handleCancel() {
  dialog.warning({
    title: '取消任务',
    content: '确定要强制中断并取消该任务吗？',
    positiveText: '确认取消',
    negativeText: '继续执行',
    onPositiveClick: async () => {
      try {
        await taskStore.cancelTask(task.value.id)
        message.info('任务已取消')
        await loadTask()
      } catch (error) {
        message.error('取消失败')
      }
    }
  })
}

async function handleExport(format) {
  try {
    const blob = await api.exportTranscript(task.value.id, format)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.value.fileName || `task-${task.value.id}`}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
    message.success(`已导出 ${format.toUpperCase()} 文件`)
  } catch (error) {
    message.error('导出失败')
  }
}

onMounted(() => {
  loadTask()
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

.transcript-box {
  background: var(--n-color-modal);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  padding: 16px;
  line-height: 1.7;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.json-box {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
}
</style>
