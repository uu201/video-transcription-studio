<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">扫描源管理</h1>
        <n-text depth="3">配置本地音视频目录，扫描后选择文件创建转录任务</n-text>
      </div>
      <n-button type="primary" @click="showAddDialog">
        <template #icon>
          <n-icon><AddOutline /></n-icon>
        </template>
        新增扫描源
      </n-button>
    </div>

    <n-alert v-if="sourceStore.sources.length === 0" type="info" :closable="false">
      <template #header>开始使用：三步完成视频转文案</template>
      <ol style="margin: 8px 0 0 20px; line-height: 1.8">
        <li><strong>添加扫描源</strong> - 点击上方「新增扫描源」按钮，配置视频目录</li>
        <li><strong>扫描并选择</strong> - 扫描后会弹窗让您选择要处理的文件</li>
        <li><strong>查看结果</strong> - 任务完成后在「处理任务」页面查看和导出文案</li>
      </ol>
    </n-alert>

    <n-card title="已配置扫描源">
      <template #header-extra>
        <n-text depth="3">共 {{ sourceStore.sources.length }} 个</n-text>
      </template>

      <n-empty v-if="sourceStore.sources.length === 0 && !sourceStore.loading" description="暂无扫描源，点击右上角添加" />

      <n-data-table
        v-else
        :columns="columns"
        :data="sourceStore.sources"
        :loading="sourceStore.loading"
        :single-line="false"
      />
    </n-card>

    <!-- 添加/编辑对话框 -->
    <n-modal v-model:show="dialogVisible" :title="editingId ? '编辑扫描源' : '新增扫描源'">
      <n-card style="width: 600px" :bordered="false" size="huge">
        <n-form :model="formData" label-placement="top">
          <n-form-item label="扫描源名称" required>
            <n-input v-model:value="formData.name" placeholder="例如：本周机位录音" />
          </n-form-item>

          <n-form-item label="目录路径" required>
            <n-input v-model:value="formData.rootPath" placeholder="例如：D:\Videos" />
          </n-form-item>

          <n-grid :cols="2" :x-gap="16">
            <n-gi>
              <n-form-item label="稳定等待秒数">
                <n-input-number v-model:value="formData.stableWaitSeconds" :min="1" :max="3600" style="width: 100%" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="处理后策略">
                <n-select v-model:value="formData.transferPolicy" :options="policyOptions" />
              </n-form-item>
            </n-gi>
          </n-grid>

          <n-form-item label="扫描选项">
            <n-space>
              <n-checkbox v-model:checked="formData.recursive">递归扫描子目录</n-checkbox>
              <n-checkbox v-model:checked="formData.autoScan">开启自动监控</n-checkbox>
            </n-space>
          </n-form-item>
        </n-form>

        <n-space justify="end">
          <n-button @click="dialogVisible = false">取消</n-button>
          <n-button
            type="primary"
            :loading="saving"
            :disabled="!formData.name || !formData.rootPath"
            @click="handleSave"
          >
            {{ editingId ? '保存变更' : '保存并扫描' }}
          </n-button>
        </n-space>
      </n-card>
    </n-modal>

    <!-- 文件选择对话框 -->
    <n-modal v-model:show="fileDialogVisible" title="选择要处理的媒体文件" style="width: 1000px">
      <n-card :bordered="false" size="huge">
        <!-- 扫描结果统计 -->
        <n-alert type="success" :closable="false" style="margin-bottom: 16px">
          <template #header>
            扫描完成
          </template>
          发现 {{ scanSummary.discovered }} 个文件，
          新增 {{ scanSummary.created }} 个，
          已存在 {{ scanSummary.skipped }} 个
          <template v-if="scanSummary.failed > 0">
            ，失败 {{ scanSummary.failed }} 个
          </template>
        </n-alert>

        <!-- 文件筛选 -->
        <n-space justify="space-between" style="margin-bottom: 16px">
          <n-radio-group v-model:value="fileFilter" size="small">
            <n-radio-button value="all">全部文件 ({{ allFiles.length }})</n-radio-button>
            <n-radio-button value="new">新发现 ({{ newFiles.length }})</n-radio-button>
            <n-radio-button value="processed">已处理 ({{ processedFiles.length }})</n-radio-button>
            <n-radio-button value="failed">处理失败 ({{ failedFiles.length }})</n-radio-button>
          </n-radio-group>

          <n-space>
            <n-button size="small" @click="selectAllAvailable">全选可用</n-button>
            <n-button size="small" @click="selectedFiles = []">取消全选</n-button>
          </n-space>
        </n-space>

        <!-- 文件列表 -->
        <n-data-table
          :columns="fileColumns"
          :data="filteredFiles"
          :row-key="row => row.id"
          v-model:checked-row-keys="selectedFiles"
          :max-height="450"
          :row-class-name="getRowClassName"
        />

        <!-- 操作区 -->
        <n-space justify="space-between" style="margin-top: 16px">
          <n-space vertical :size="4">
            <n-tag v-if="selectedFiles.length > 0" type="success">
              已选择 {{ selectedFiles.length }} / {{ filteredFiles.length }} 个文件
            </n-tag>
            <n-text v-else depth="3" style="font-size: 12px">
              提示：只能选择未处理或处理失败的文件
            </n-text>
          </n-space>

          <n-space>
            <n-button @click="fileDialogVisible = false">取消</n-button>
            <n-button
              type="primary"
              :disabled="selectedFiles.length === 0"
              :loading="creating"
              @click="createTasks"
            >
              创建 {{ selectedFiles.length }} 个任务
            </n-button>
          </n-space>
        </n-space>
      </n-card>
    </n-modal>
  </n-space>
</template>

<script setup>
import { ref, h, computed, onMounted } from 'vue'
import { NButton, NTag, NIcon, NTooltip, useMessage, useDialog } from 'naive-ui'
import { Add as AddOutline, Search as SearchOutline, Create as CreateOutline, Trash as TrashOutline } from '@vicons/ionicons5'
import { useSourceStore } from '@/stores/source'
import { formatDateTime } from '@/utils/format'
import api from '@/api'

const message = useMessage()
const dialog = useDialog()
const sourceStore = useSourceStore()

const dialogVisible = ref(false)
const fileDialogVisible = ref(false)
const editingId = ref(null)
const saving = ref(false)
const creating = ref(false)
const allFiles = ref([])
const selectedFiles = ref([])
const currentSourceId = ref(null)
const fileFilter = ref('all')
const scanSummary = ref({
  discovered: 0,
  created: 0,
  skipped: 0,
  failed: 0
})

const formData = ref({
  name: '',
  rootPath: '',
  recursive: true,
  stableWaitSeconds: 5,
  autoScan: false,
  transferPolicy: 'keep',
  resultDir: null
})

const policyOptions = [
  { label: '保留源文件', value: 'keep' },
  { label: '复制到结果目录', value: 'copy' },
  { label: '移动到归档目录', value: 'move' }
]

// 文件过滤
const newFiles = computed(() => allFiles.value.filter(f => f.is_new))
const processedFiles = computed(() => allFiles.value.filter(f => f.task_count > 0 && f.latest_status === 'completed'))
const failedFiles = computed(() => allFiles.value.filter(f => f.latest_status === 'failed'))

const filteredFiles = computed(() => {
  switch (fileFilter.value) {
    case 'new':
      return newFiles.value
    case 'processed':
      return processedFiles.value
    case 'failed':
      return failedFiles.value
    default:
      return allFiles.value
  }
})

// 状态标签映射
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

const columns = [
  {
    type: 'selection'
  },
  {
    title: '扫描源名称',
    key: 'name',
    render: (row) => {
      return h('div', [
        h('div', { style: 'font-weight: 600; margin-bottom: 4px' }, row.name),
        h('div', { style: 'font-size: 11px; opacity: 0.6; font-family: monospace; word-break: break-all' }, row.rootPath || row.root_path || row.path)
      ])
    }
  },
  {
    title: '递归子目录',
    key: 'recursive',
    width: 100,
    render: (row) => h(NTag, { type: row.recursive ? 'success' : 'default', size: 'small' }, { default: () => row.recursive ? '是' : '否' })
  },
  {
    title: '最近扫描',
    key: 'updatedAt',
    width: 160,
    render: (row) => formatDateTime(row.updatedAt || row.updated_at)
  },
  {
    title: '操作',
    key: 'actions',
    width: 280,
    render: (row) => {
      return h('div', { style: 'display: flex; gap: 8px' }, [
        h(NButton, {
          text: true,
          type: 'primary',
          size: 'small',
          onClick: () => handleScan(row.id)
        }, {
          default: () => '立即扫描',
          icon: () => h(NIcon, null, { default: () => h(SearchOutline) })
        }),
        h(NButton, {
          text: true,
          type: 'primary',
          size: 'small',
          onClick: () => handleEdit(row)
        }, {
          default: () => '编辑',
          icon: () => h(NIcon, null, { default: () => h(CreateOutline) })
        }),
        h(NButton, {
          text: true,
          type: 'error',
          size: 'small',
          onClick: () => handleDelete(row.id)
        }, {
          default: () => '删除',
          icon: () => h(NIcon, null, { default: () => h(TrashOutline) })
        })
      ])
    }
  }
]

const fileColumns = [
  {
    type: 'selection',
    disabled: (row) => !row.can_select
  },
  {
    title: '文件名',
    key: 'file_name',
    ellipsis: { tooltip: true }
  },
  {
    title: '大小',
    key: 'size_display',
    width: 100
  },
  {
    title: '状态',
    key: 'latest_status',
    width: 120,
    render: (row) => {
      if (row.is_new) {
        return h(NTag, { type: 'info', size: 'small' }, { default: () => '新发现' })
      }
      if (!row.latest_status) {
        return h(NTag, { type: 'default', size: 'small' }, { default: () => '未处理' })
      }
      return h(NTag, {
        type: statusTypeMap[row.latest_status] || 'default',
        size: 'small'
      }, {
        default: () => statusLabelMap[row.latest_status] || row.latest_status
      })
    }
  },
  {
    title: '处理次数',
    key: 'task_count',
    width: 100,
    render: (row) => row.task_count || 0
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => {
      if (row.can_select) {
        return h('span', { style: 'color: var(--n-text-color-success)' }, '可处理')
      }
      return h(
        NTooltip,
        null,
        {
          trigger: () => h('span', { style: 'color: var(--n-text-color-disabled)' }, '不可选'),
          default: () => '已处理完成或正在处理中'
        }
      )
    }
  }
]

function getRowClassName(row) {
  if (!row.can_select) {
    return 'disabled-row'
  }
  if (row.is_new) {
    return 'new-row'
  }
  return ''
}

function selectAllAvailable() {
  selectedFiles.value = filteredFiles.value
    .filter(f => f.can_select)
    .map(f => f.id)
}

function showAddDialog() {
  editingId.value = null
  formData.value = {
    name: '',
    rootPath: '',
    recursive: true,
    stableWaitSeconds: 5,
    autoScan: false,
    transferPolicy: 'keep',
    resultDir: null
  }
  dialogVisible.value = true
}

function handleEdit(row) {
  editingId.value = row.id
  formData.value = {
    name: row.name,
    rootPath: row.rootPath || row.root_path || row.path || '',
    recursive: row.recursive,
    stableWaitSeconds: row.stableWaitSeconds || row.stable_wait_seconds || 5,
    autoScan: row.autoScan || row.auto_scan || false,
    transferPolicy: row.transferPolicy || row.transfer_policy || 'keep',
    resultDir: row.resultDir || row.result_dir || null
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editingId.value) {
      await sourceStore.updateSource(editingId.value, formData.value)
      message.success('扫描源配置已更新')
      dialogVisible.value = false
    } else {
      const newSource = await sourceStore.createSource(formData.value)
      dialogVisible.value = false
      message.success('扫描源已添加，开始扫描...')
      if (newSource && newSource.id) {
        await handleScan(newSource.id)
      } else {
        await sourceStore.fetchSources()
        if (sourceStore.sources.length > 0) {
          await handleScan(sourceStore.sources[0].id)
        }
      }
    }
  } catch (error) {
    console.error('保存失败:', error)
    message.error(error.response?.data?.detail || '操作失败，请检查输入')
  } finally {
    saving.value = false
  }
}

async function handleScan(id) {
  try {
    const result = await sourceStore.scanSource(id)

    // 保存扫描统计
    scanSummary.value = {
      discovered: result.discovered || 0,
      created: result.created || 0,
      skipped: result.skipped || 0,
      failed: result.failed || 0
    }

    // 保存文件列表
    allFiles.value = result.files || []

    if (allFiles.value.length > 0) {
      currentSourceId.value = id
      selectedFiles.value = []
      fileFilter.value = 'all'
      fileDialogVisible.value = true
    } else {
      message.info('该目录下未发现支持的媒体文件')
    }
  } catch (error) {
    console.error('扫描失败:', error)
    message.error('扫描失败，请检查目录路径')
  }
}

async function createTasks() {
  creating.value = true
  try {
    await api.createTasks({
      mediaFileIds: selectedFiles.value,
      language: 'auto'
    })
    message.success(`已创建 ${selectedFiles.value.length} 个处理任务`)
    fileDialogVisible.value = false
  } catch (error) {
    message.error('创建任务失败')
  } finally {
    creating.value = false
  }
}

function handleDelete(id) {
  dialog.warning({
    title: '删除扫描源',
    content: '确定要移除此扫描源吗？这不会删除磁盘上的物理文件。',
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await sourceStore.deleteSource(id)
        message.success('扫描源已删除')
      } catch (error) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => {
  sourceStore.fetchSources()
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

:deep(.disabled-row) {
  opacity: 0.5;
  background-color: var(--n-td-color-striped);
}

:deep(.new-row) {
  background-color: rgba(24, 160, 88, 0.05);
}
</style>
