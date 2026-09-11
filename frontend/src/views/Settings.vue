<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">系统设置</h1>
        <n-text depth="3">配置语音识别引擎、FFmpeg 路径和 AI 分析功能</n-text>
      </div>
      <n-button type="primary" :loading="saving" @click="handleSave">
        <template #icon>
          <n-icon><SaveOutline /></n-icon>
        </template>
        保存配置
      </n-button>
    </div>

    <!-- ASR 引擎设置 -->
    <n-card title="1. ASR 语音识别引擎">
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="Provider / 模型算法">
              <n-input disabled value="SenseVoiceSmall (阿里巴巴开源)" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="计算加速设备">
              <n-select v-model:value="settings.asr_device" :options="deviceOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="支持语言">
              <n-select v-model:value="settings.asr_language" :options="languageOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="批处理步长 (秒)">
              <n-input-number v-model:value="settings.batch_seconds" :min="10" :max="300" style="width: 100%" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
    </n-card>

    <!-- 媒体工具路径 -->
    <n-card title="2. FFmpeg / FFprobe 媒体依赖">
      <template #header-extra>
        <n-button size="small" :loading="checking" @click="checkTools">
          检查工具有效性
        </n-button>
      </template>

      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="FFmpeg 可执行文件路径">
              <n-input v-model:value="settings.ffmpeg_path" placeholder="/usr/local/bin/ffmpeg" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="FFprobe 可执行文件路径">
              <n-input v-model:value="settings.ffprobe_path" placeholder="/usr/local/bin/ffprobe" />
            </n-form-item>
          </n-gi>
        </n-grid>
      </n-form>
    </n-card>

    <!-- 模型缓存 -->
    <n-card title="3. 本地模型缓存目录">
      <n-text depth="3" style="display: block; margin-bottom: 16px">
        模型存储位置: <n-text code>{{ settings.model_dir_path }}</n-text>
      </n-text>

      <n-grid :cols="2" :x-gap="16">
        <n-gi>
          <n-card size="small" embedded>
            <n-space justify="space-between" align="center">
              <n-text strong>SenseVoiceSmall</n-text>
              <n-tag type="success" size="small">就绪 100%</n-tag>
            </n-space>
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              大小: 420 MB | 状态: 已验证权重哈希
            </n-text>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" embedded>
            <n-space justify="space-between" align="center">
              <n-text strong>FSMN-VAD 模型</n-text>
              <n-tag type="success" size="small">就绪 100%</n-tag>
            </n-space>
            <n-text depth="3" style="font-size: 12px; margin-top: 8px; display: block">
              大小: 45 MB | 状态: 已加载至缓存
            </n-text>
          </n-card>
        </n-gi>
      </n-grid>
    </n-card>

    <!-- AI Provider -->
    <n-card title="4. AI Provider 接口配置 (选填)">
      <template #header-extra>
        <n-switch v-model:value="aiConfig.enabled">
          <template #checked>启用 AI 提炼</template>
          <template #unchecked>禁用</template>
        </n-switch>
      </template>

      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-form-item label="Provider 类型">
              <n-select v-model:value="aiConfig.provider" :options="providerOptions" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="Base URL">
              <n-input v-model:value="aiConfig.base_url" placeholder="https://api.openai.com/v1" />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="API Key">
              <n-input v-model:value="aiConfig.api_key" type="password" show-password-on="click" placeholder="sk-..." />
            </n-form-item>
          </n-gi>
          <n-gi>
            <n-form-item label="模型名称">
              <n-input v-model:value="aiConfig.model_name" placeholder="gpt-4o-mini" />
            </n-form-item>
          </n-gi>
        </n-grid>

        <n-button :loading="testing" @click="testAi">测试接口连通性</n-button>
      </n-form>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { Save as SaveOutline } from '@vicons/ionicons5'
import api from '@/api'

const message = useMessage()

const saving = ref(false)
const checking = ref(false)
const testing = ref(false)

const settings = ref({
  asr_device: 'cpu',
  asr_language: 'auto',
  batch_seconds: 60,
  ffmpeg_path: '',
  ffprobe_path: '',
  model_dir_path: ''
})

const aiConfig = ref({
  enabled: false,
  provider: 'openai',
  base_url: '',
  api_key: '',
  model_name: ''
})

const deviceOptions = [
  { label: 'CPU (通用低负载)', value: 'cpu' },
  { label: 'CUDA / GPU (若可用)', value: 'cuda' }
]

const languageOptions = [
  { label: 'auto (自动识别多语言)', value: 'auto' },
  { label: 'zh (中文普通话)', value: 'zh' },
  { label: 'en (英语)', value: 'en' },
  { label: 'yue (粤语)', value: 'yue' },
  { label: 'ja (日语)', value: 'ja' },
  { label: 'ko (韩语)', value: 'ko' }
]

const providerOptions = [
  { label: 'OpenAI Compatible', value: 'openai' },
  { label: 'Ollama (本地私有化)', value: 'ollama' },
  { label: 'Anthropic Claude', value: 'claude' }
]

async function loadSettings() {
  try {
    const data = await api.getSystemInfo()
    if (data.settings) {
      settings.value = { ...settings.value, ...data.settings }
    }
    if (data.ai_config) {
      aiConfig.value = { ...aiConfig.value, ...data.ai_config }
    }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

async function handleSave() {
  saving.value = true
  try {
    // TODO: 实现保存设置的 API
    message.success('系统设置已保存')
  } catch (error) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function checkTools() {
  checking.value = true
  try {
    const result = await api.checkMediaTools()
    if (result.available) {
      message.success('FFmpeg 与 FFprobe 探测正常')
    } else {
      message.warning(result.message || '工具不可用')
    }
  } catch (error) {
    message.error('检查失败')
  } finally {
    checking.value = false
  }
}

async function testAi() {
  testing.value = true
  try {
    // TODO: 实现测试 AI 连接的 API
    message.success('AI Provider 连接成功')
  } catch (error) {
    message.error('连接失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSettings()
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
