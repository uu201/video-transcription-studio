<template>
  <n-config-provider :theme="theme" :theme-overrides="themeOverrides">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-layout class="app-layout">
            <router-view />
          </n-layout>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { computed } from 'vue'
import { darkTheme, NConfigProvider, NMessageProvider, NDialogProvider, NNotificationProvider, NLayout } from 'naive-ui'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

const theme = computed(() => appStore.isDark ? darkTheme : null)

// 主题覆盖配置
const themeOverrides = computed(() => {
  if (appStore.isDark) {
    // 深色主题配置
    return {
      common: {
        primaryColor: '#d9f36b',
        primaryColorHover: '#e5f889',
        primaryColorPressed: '#c5e055',
        primaryColorSuppl: '#d9f36b',

        // 深色模式文本对比度优化
        textColorBase: '#e8e8e8',
        textColor1: '#ffffff',
        textColor2: '#e0e0e0',
        textColor3: '#b4b4b4',

        // 背景色
        bodyColor: '#101014',
        cardColor: '#18181c',
        modalColor: '#18181c',
        popoverColor: '#18181c',

        borderRadius: '8px'
      },
      Card: {
        borderColor: 'rgba(255, 255, 255, 0.09)'
      },
      DataTable: {
        thColor: 'rgba(255, 255, 255, 0.05)',
        thTextColor: '#d0d0d0'
      }
    }
  } else {
    // 浅色主题配置
    return {
      common: {
        primaryColor: '#18a058',
        primaryColorHover: '#36ad6a',
        primaryColorPressed: '#0c7a43',
        primaryColorSuppl: '#18a058',

        // 浅色模式文本对比度优化
        textColorBase: '#000000',
        textColor1: '#000000',
        textColor2: '#333333',
        textColor3: '#666666',

        // 背景色
        bodyColor: '#ffffff',
        cardColor: '#ffffff',
        modalColor: '#ffffff',
        popoverColor: '#ffffff',

        borderRadius: '8px'
      },
      Card: {
        borderColor: 'rgba(0, 0, 0, 0.09)'
      },
      DataTable: {
        thColor: 'rgba(0, 0, 0, 0.02)',
        thTextColor: '#666666'
      }
    }
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "PingFang SC", "Microsoft YaHei", "微软雅黑", "Helvetica Neue", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-layout {
  min-height: 100vh;
}

/* 滚动条样式优化 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(128, 128, 128, 0.5);
}
</style>
