<template>
  <n-spin :show="loading">
    <n-space vertical :size="24" v-if="task">
      <div class="page-header">
        <div>
          <n-button text @click="router.push(isResultDetail ? '/results' : '/tasks')" style="margin-bottom: 8px">
            <template #icon>
              <n-icon><ArrowBackOutline /></n-icon>
            </template>
            {{ isResultDetail ? '返回转录结果' : '返回任务列表' }}
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

      <n-card v-if="task.status === 'SUCCEEDED' && !isResultDetail" title="转录结果已就绪">
        <n-space align="center" justify="space-between" wrap>
          <n-text depth="2">正文、时间戳分段和 AI 处理结果已移至「转录结果」书架，便于集中阅读和复用。</n-text>
          <n-button type="primary" @click="router.push(`/results/${task.id}`)">
            <template #icon><n-icon><DocumentOutline /></n-icon></template>
            查看转录结果
          </n-button>
        </n-space>
      </n-card>

      <!-- 转写结果 -->
      <n-card v-if="task.status === 'SUCCEEDED' && isResultDetail" title="转写文案资产">
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

      <!-- AI 处理结果 -->
      <n-card v-if="task.status === 'SUCCEEDED' && isResultDetail" title="AI 处理结果">
        <template #header-extra>
          <n-tag v-if="analyses.length > 0" type="success" size="small">{{ analyses.length }} 项结果</n-tag>
          <n-tag v-else type="default" size="small">尚未生成</n-tag>
        </template>

        <n-space v-if="analyses.length > 0" vertical :size="12" style="width: 100%">
          <n-card
            v-for="analysis in analyses"
            :key="analysis.id"
            size="small"
            embedded
            :bordered="true"
          >
            <template #header>
              <n-space align="center" :size="8">
                <n-tag type="info" size="small">{{ analysisTypeLabel(analysis.analysisType) }}</n-tag>
                <n-tag :type="analysisStatusType(analysis.status)" size="small">
                  {{ analysisStatusLabel(analysis.status) }}
                </n-tag>
              </n-space>
            </template>
            <template #header-extra>
              <n-text depth="3" style="font-size: 12px">{{ formatDateTime(analysis.createdAt) }}</n-text>
            </template>
            <div class="analysis-content">{{ analysis.content || '该分析暂无可显示内容' }}</div>
            <n-text v-if="analysis.providerName || analysis.model" depth="3" class="analysis-meta">
              {{ analysis.providerName || 'AI 服务' }}<span v-if="analysis.model"> · {{ analysis.model }}</span>
              <span v-if="analysis.promptVersion"> · 提示词 v{{ analysis.promptVersion }}</span>
            </n-text>
          </n-card>
        </n-space>
        <n-empty v-else description="当前结果还没有 AI 处理内容">
          <template #extra>
            <n-text depth="3">AI 分析功能尚未生成可展示的记录，原始转写内容仍可正常使用。</n-text>
          </template>
        </n-empty>
      </n-card>

      <!-- 时间轴分段 -->
      <n-card v-if="isResultDetail && segments.length > 0" title="时间戳句子分段">
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
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const taskStore = useTaskStore()

const loading = ref(false)
const task = ref(null)
const activeTab = ref('clean')
const analyses = ref([])
const isResultDetail = computed(() => route.name === 'ResultDetail' || route.path.startsWith('/results/'))

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

const analysisTypeLabels = {
  summary: '内容摘要',
  outline: '内容大纲',
  keywords: '关键词',
  chapters: '章节整理',
  translation: '翻译结果'
}

function analysisTypeLabel(value) {
  return analysisTypeLabels[String(value || '').toLowerCase()] || value || 'AI 分析'
}

function analysisStatusLabel(value) {
  return ({ SUCCEEDED: '已完成', RUNNING: '处理中', FAILED: '失败', DISABLED: '未启用' })[value] || value || '未知状态'
}

function analysisStatusType(value) {
  return ({ SUCCEEDED: 'success', RUNNING: 'warning', FAILED: 'error', DISABLED: 'default' })[value] || 'default'
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

async function loadTask() {
  loading.value = true
  try {
    const id = route.params.id
    const detail = await taskStore.getTaskDetail(id)
    if (!detail) throw new Error('任务详情不存在')
    const [transcriptResult, segmentsResult, analysesResult] = await Promise.all([
      api.getTranscript(id).catch(() => null),
      api.getTaskSegments(id).catch(() => []),
      api.getTaskAnalyses(id).catch(() => [])
    ])
    analyses.value = Array.isArray(analysesResult) ? analysesResult : []
    task.value = { ...detail, transcript: transcriptResult, segments: segmentsResult }
  } catch (error) {
    message.error('加载任务详情失败')
    router.push(isResultDetail.value ? '/results' : '/tasks')
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

.analysis-content {
  white-space: pre-wrap;
  line-height: 1.7;
  color: var(--n-text-color-2);
}

.analysis-meta {
  display: block;
  margin-top: 12px;
  font-size: 12px;
}
</style>
