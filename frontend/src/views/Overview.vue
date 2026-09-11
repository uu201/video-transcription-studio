<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">内容处理总览</h1>
        <n-text depth="3">把本地视频素材转换成可检索、可编辑、可复用的文案资产</n-text>
      </div>
      <n-space>
        <n-button @click="router.push('/sources')">
          <template #icon>
            <n-icon><FolderAddOutline /></n-icon>
          </template>
          配置扫描源
        </n-button>
        <n-button type="primary" :loading="envLoading" @click="checkEnvironment">
          <template #icon>
            <n-icon><RefreshOutline /></n-icon>
          </template>
          重新检测环境
        </n-button>
      </n-space>
    </div>

    <!-- 统计卡片 -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" :collapsed-rows="2">
      <n-gi>
        <n-card embedded>
          <n-skeleton v-if="taskStore.loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="待处理" :value="taskStore.taskStats.pending" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              排队等待音频提取与切片
            </n-text>
          </template>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card embedded>
          <n-skeleton v-if="taskStore.loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="处理中" :value="taskStore.taskStats.processing" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              当前 SenseVoice 正在识别
            </n-text>
          </template>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card embedded>
          <n-skeleton v-if="taskStore.loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="已完成" :value="taskStore.taskStats.completed" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              文案提取完毕，支持多格式导出
            </n-text>
          </template>
        </n-card>
      </n-gi>
      <n-gi>
        <n-card embedded>
          <n-skeleton v-if="taskStore.loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="处理失败" :value="taskStore.taskStats.failed" />
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              存在环境缺失或损坏媒体
            </n-text>
          </template>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 环境检测 -->
    <n-card title="本地运行时与模型环境检测">
      <template #header-extra>
        <n-tag v-if="!envLoading" :type="envReady ? 'success' : 'warning'" size="small">
          {{ envReady ? '环境就绪' : '需要处理' }}
        </n-tag>
      </template>

      <!-- 加载骨架屏 -->
      <n-space v-if="envLoading" vertical :size="12">
        <n-skeleton v-for="i in 9" :key="i" text style="width: 100%" />
      </n-space>

      <!-- 空状态 -->
      <n-empty v-else-if="envItems.length === 0" description="点击右上角按钮检测环境" />

      <!-- 环境列表 -->
      <n-list v-else bordered>
        <n-list-item v-for="item in envItems" :key="item.key">
          <template #prefix>
            <n-tag
              :type="item.status === 'ok' ? 'success' : (item.status === 'warn' ? 'warning' : 'error')"
              size="small"
              round
            >
              {{ item.status === 'ok' ? '✓' : (item.status === 'warn' ? '!' : '✗') }}
            </n-tag>
          </template>

          <n-thing>
            <template #header>
              {{ item.label }}
            </template>
            <template #description>
              <n-space vertical :size="4">
                <n-text depth="2">{{ item.value }}</n-text>
                <n-text depth="3" style="font-size: 12px">{{ item.detail }}</n-text>
              </n-space>
            </template>
          </n-thing>

          <template #suffix>
            <n-tag
              :type="item.status === 'ok' ? 'success' : (item.status === 'warn' ? 'warning' : 'error')"
              size="small"
            >
              {{ item.status === 'ok' ? '正常' : (item.status === 'warn' ? '警告' : '异常') }}
            </n-tag>
          </template>
        </n-list-item>
      </n-list>

      <!-- 检测时间 -->
      <n-text v-if="checkedAt && !envLoading" depth="3" style="display: block; margin-top: 12px; font-size: 12px">
        检测时间：{{ checkedAt }}
      </n-text>
    </n-card>

    <!-- 最近任务 -->
    <n-card title="最近处理记录">
      <template #header-extra>
        <n-button text type="primary" @click="router.push('/tasks')">
          查看全部任务 →
        </n-button>
      </template>

      <!-- 加载骨架屏 -->
      <n-space v-if="taskStore.loading" vertical :size="12">
        <n-skeleton v-for="i in 3" :key="i" text style="width: 100%" />
      </n-space>

      <!-- 空状态 -->
      <n-empty v-else-if="taskStore.tasks.length === 0" description="还没有处理记录，请先添加扫描源">
        <template #extra>
          <n-button type="primary" @click="router.push('/sources')">
            <template #icon>
              <n-icon><FolderAddOutline /></n-icon>
            </template>
            前往配置扫描源
          </n-button>
        </template>
      </n-empty>

      <!-- 任务列表 -->
      <n-data-table
        v-else
        :columns="taskColumns"
        :data="recentTasks"
        :pagination="false"
        :single-line="false"
      />
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, useMessage } from 'naive-ui'
import { FolderOpen as FolderAddOutline, Refresh as RefreshOutline } from '@vicons/ionicons5'
import { useTaskStore } from '@/stores/task'
import api from '@/api'

const router = useRouter()
const message = useMessage()
const taskStore = useTaskStore()

const envLoading = ref(true)
const envReady = ref(false)
const envItems = ref([])
const checkedAt = ref('')

const recentTasks = computed(() => taskStore.tasks.slice(0, 5))

const statusTypeMap = {
  pending: 'default',
  processing: 'warning',
  completed: 'success',
  failed: 'error'
}

const statusLabelMap = {
  pending: '等待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败'
}

const taskColumns = [
  {
    title: '文件名',
    key: 'file_name',
    ellipsis: { tooltip: true },
    render: (row) => row.file_name || row.fileName || '未知文件'
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row) => {
      return h(NTag, {
        type: statusTypeMap[row.status] || 'default',
        size: 'small'
      }, {
        default: () => statusLabelMap[row.status] || row.status
      })
    }
  },
  {
    title: '进度',
    key: 'progress',
    width: 100,
    render: (row) => `${row.progress || 0}%`
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row) => {
      return h(
        NButton,
        {
          text: true,
          type: 'primary',
          size: 'small',
          onClick: () => router.push(`/tasks/${row.id}`)
        },
        { default: () => '查看详情' }
      )
    }
  }
]

async function checkEnvironment() {
  envLoading.value = true
  try {
    const data = await api.getEnvironment(true)

    // 解析环境数据
    if (data.overall) {
      envReady.value = data.overall === 'ok'
    }

    if (data.checkedAt) {
      checkedAt.value = new Date(data.checkedAt).toLocaleString('zh-CN')
    }

    if (data.items && Array.isArray(data.items)) {
      envItems.value = data.items
    }

    message.success('环境检测完成')
  } catch (error) {
    console.error('环境检测失败:', error)
    message.error('环境检测失败，请检查后端服务')
    envItems.value = []
  } finally {
    envLoading.value = false
  }
}

onMounted(async () => {
  // 并行加载任务和环境
  await Promise.all([
    taskStore.fetchTasks(),
    checkEnvironment()
  ])
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
