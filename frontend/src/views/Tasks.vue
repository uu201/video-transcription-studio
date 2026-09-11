<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">处理任务</h1>
        <n-text depth="3">查看转录任务状态，下载完成的文案，重试失败的任务</n-text>
      </div>
      <n-button @click="taskStore.fetchTasks">
        <template #icon>
          <n-icon><RefreshOutline /></n-icon>
        </template>
        刷新列表
      </n-button>
    </div>

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
          <n-radio-button value="SUCCEEDED">已完成 ({{ taskStore.taskStats.completed }})</n-radio-button>
          <n-radio-button value="FAILED">失败 ({{ taskStore.taskStats.failed }})</n-radio-button>
        </n-radio-group>
      </n-space>
    </n-card>

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
import { ref, computed, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NProgress, NIcon, useMessage, useDialog } from 'naive-ui'
import { Refresh as RefreshOutline, Search as SearchOutline, DocumentText as DocumentTextOutline, RefreshCircle as RefreshCircleOutline, CloseCircle as CloseCircleOutline, Trash as TrashOutline } from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const taskStore = useTaskStore()

const searchKeyword = ref('')
const filterStatus = ref('all')

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
      (t.file_path || t.filePath || '').toLowerCase().includes(keyword)
    )
  }

  return result
})

const statusTypeMap = {
  QUEUED: 'default',
  RUNNING: 'warning',
  SUCCEEDED: 'success',
  FAILED: 'error',
  CANCELED: 'default'
}

const statusLabelMap = {
  QUEUED: '等待处理',
  RUNNING: '处理中',
  SUCCEEDED: '已完成',
  FAILED: '失败',
  CANCELED: '已取消'
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
      const filePath = row.file_path || row.filePath || ''
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
    render: (row) => h('span', { style: 'font-size: 12px' }, row.stage || '--')
  },
  {
    title: '总进度',
    key: 'progress',
    width: 130,
    render: (row) => h(NProgress, {
      type: 'line',
      percentage: row.progress || 0,
      status: row.status === 'FAILED' ? 'error' : (row.status === 'SUCCEEDED' ? 'success' : 'default'),
      showIndicator: true
    })
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 160,
    render: (row) => row.updated_at || row.updatedAt || '--'
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

      if (row.status === 'RUNNING') {
        actions.push(
          h(NButton, {
            text: true,
            type: 'warning',
            size: 'small',
            onClick: () => handleCancel(row.id)
          }, {
            default: () => '取消',
            icon: () => h(NIcon, null, { default: () => h(CloseCircleOutline) })
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

      if (row.status === 'FAILED' || row.status === 'CANCELED') {
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

async function handleRetry(id) {
  try {
    await taskStore.retryTask(id)
    message.success('任务已重新加入队列')
  } catch (error) {
    message.error('重试失败')
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
  taskStore.fetchTasks()
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
</style>
