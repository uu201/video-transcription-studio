<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      bordered
      :width="240"
      :collapsed-width="64"
      :collapsed="collapsed"
      show-trigger
      collapse-mode="width"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="sidebar-header">
        <div class="brand-logo">转</div>
        <div v-if="!collapsed" class="brand-info">
          <div class="brand-title">视频转文案</div>
          <div class="brand-subtitle">本地化语音识别</div>
        </div>
      </div>

      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="currentRoute"
        @update:value="handleMenuSelect"
      />

      <div v-if="!collapsed" class="sidebar-footer">
        <n-space vertical :size="4">
          <n-text depth="3" style="font-size: 12px">本地引擎运行中</n-text>
          <n-text depth="3" style="font-size: 11px">版本 v0.1.0</n-text>
        </n-space>
      </div>
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between">
        <n-breadcrumb>
          <n-breadcrumb-item>工作台</n-breadcrumb-item>
          <n-breadcrumb-item>{{ currentPageTitle }}</n-breadcrumb-item>
        </n-breadcrumb>

        <n-space>
          <n-button circle @click="appStore.toggleTheme" size="small">
            <template #icon>
              <n-icon>
                <component :is="appStore.isDark ? SunnyOutline : MoonOutline" />
              </n-icon>
            </template>
          </n-button>
        </n-space>
      </n-layout-header>

      <n-layout-content content-style="padding: 24px">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  Grid as GridOutline,
  FolderOpen as FolderOpenOutline,
  List as ListOutline,
  Sparkles as SparklesOutline,
  LibraryOutline,
  Settings as SettingsOutline,
  Sunny as SunnyOutline,
  Moon as MoonOutline
} from '@vicons/ionicons5'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

const collapsed = ref(false)

const renderIcon = (icon) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = [
  {
    label: '总览',
    key: 'overview',
    icon: renderIcon(GridOutline)
  },
  {
    label: '扫描源',
    key: 'sources',
    icon: renderIcon(FolderOpenOutline)
  },
  {
    label: '处理任务',
    key: 'tasks',
    icon: renderIcon(ListOutline)
  },
  {
    label: 'AI 分析',
    key: 'ai-analysis',
    icon: renderIcon(SparklesOutline)
  },
  {
    label: '转录结果',
    key: 'results',
    icon: renderIcon(LibraryOutline)
  },
  {
    label: '系统设置',
    key: 'settings',
    icon: renderIcon(SettingsOutline)
  }
]

const currentRoute = computed(() => {
  const name = route.name
  if (name === 'TaskDetail') return 'tasks'
  if (name === 'ResultDetail') return 'results'
  return route.path.split('/')[1] || 'overview'
})

const currentPageTitle = computed(() => {
  const titles = {
    overview: '内容处理总览',
    sources: '扫描源配置',
    tasks: '处理任务队列',
    'ai-analysis': 'AI 分析队列',
    results: '转录结果书架',
    settings: '系统环境设置'
  }
  return titles[currentRoute.value] || '工作台'
})

function handleMenuSelect(key) {
  router.push(`/${key}`)
}
</script>

<style scoped>
.sidebar-header {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--n-border-color);
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #d9f36b;
  color: #131a08;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.brand-title {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.3;
}

.brand-subtitle {
  font-size: 11px;
  opacity: 0.65;
  line-height: 1.3;
}

.sidebar-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  border-top: 1px solid var(--n-border-color);
}
</style>
