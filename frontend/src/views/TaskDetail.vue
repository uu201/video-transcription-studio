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
          <h1 class="page-title">#{{ task.id }} - {{ task.file_name }}</h1>
          <n-text depth="3" style="word-break: break-all">{{ task.file_path }}</n-text>
        </div>
        <n-space>
          <n-button v-if="task.status === 'failed'" type="warning" @click="handleRetry">
            <template #icon>
              <n-icon><RefreshCircleOutline /></n-icon>
            </template>
            重新尝试
          </n-button>
          <n-button v-if="task.status === 'processing'" type="error" @click="handleCancel">
            <template #icon>
              <n-icon><CloseCircleOutline /></n-icon>
            </template>
            终止任务
          </n-button>
          <n-button v-if="task.status === 'completed'" type="success" disabled>
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
            <n-statistic label="媒体时长" :value="task.duration || '--'" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              大小: {{ task.file_size || '--' }}
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="分辨率" :value="task.resolution || '仅音频'" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              音频: {{ task.audio_format || 'N/A' }}
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
              阶段: {{ task.current_stage || '--' }}
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small">
            <n-statistic label="总体进度" :value="`${task.progress || 0}%`" />
            <n-progress
              type="line"
              :percentage="task.progress || 0"
              :status="task.status === 'failed' ? 'error' : (task.status === 'completed' ? 'success' : 'default')"
              :show-indicator="false"
              style="margin-top: 8px"
            />
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 错误信息 -->
      <n-alert v-if="task.status === 'failed' && task.message" type="error" title="任务执行中断">
        {{ task.message }}
      </n-alert>

      <!-- 转写结果 -->
      <n-card v-if="task.status === 'completed'" title="转写文案资产">
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
            <div class="transcript-box">
              {{ task.transcript?.clean_text || '暂无内容' }}
            </div>
          </n-tab-pane>
          <n-tab-pane name="raw" tab="原始识别文本">
            <div class="transcript-box">
              {{ task.transcript?.raw_text || '暂无内容' }}
            </div>
          </n-tab-pane>
          <n-tab-pane name="json" tab="完整 JSON">
            <div class="transcript-box" style="font-family: monospace; font-size: 12px">
              {{ JSON.stringify(task.transcript, null, 2) }}
            </div>
          </n-tab-pane>
        </n-tabs>
      </n-card>

      <!-- 时间轴分段 -->
      <n-card v-if="task.segments && task.segments.length > 0" title="时间戳句子分段">
        <template #header-extra>
          <n-text depth="3">共 {{ task.segments.length }} 段</n-text>
        </template>

        <n-data-table
          :columns="segmentColumns"
          :data="task.segments"
          :pagination="{ pageSize: 10 }"
          size="small"
        />
      </n-card>

      <!-- 处理流程时间线 -->
      <n-card title="处理全流程时间线">
        <n-timeline>
          <n-timeline-item
            v-for="(step, idx) in task.pipeline"
            :key="idx"
            :type="step.status === 'done' ? 'success' : (step.status === 'error' ? 'error' : 'default')"
            :title="step.name"
            :content="step.desc"
            :time="step.time"
          />
        </n-timeline>
      </n-card>
    </n-space>
  </n-spin>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

const statusTypeMap = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default'
}

const statusLabelMap = {
  pending: '等待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消'
}

const segmentColumns = [
  { title: '#', key: 'id', width: 50 },
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
    render: (row) => `${(row.confidence * 100).toFixed(0)}%`
  }
]

async function loadTask() {
  loading.value = true
  try {
    const id = route.params.id
    task.value = await taskStore.getTaskDetail(id)
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
    a.download = `${task.value.file_name}.${format}`
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
</style>
