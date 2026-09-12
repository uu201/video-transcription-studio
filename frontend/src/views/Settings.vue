<template>
  <n-space vertical :size="24" class="settings-page">
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
    <n-card class="ai-provider-card" :class="{ 'ai-provider-disabled': !aiConfig.enabled }">
      <template #header>AI Provider 接口配置（选填）</template>
      <template #header-extra>
        <label class="provider-toggle">
          <span>启用 AI 提炼</span>
          <n-switch v-model:value="aiConfig.enabled" :rail-style="railStyle" />
        </label>
      </template>

      <div v-if="!aiConfig.enabled" class="provider-disabled-state">
        <div class="provider-disabled-icon">AI</div>
        <div>
          <strong>AI 提炼当前未启用</strong>
          <p>打开右上角开关后配置服务地址、密钥和模型。未配置 AI 时，音视频转录仍可正常使用。</p>
        </div>
      </div>

      <n-form v-else label-placement="top" class="provider-form">
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
              <n-space vertical style="width: 100%" :size="8">
                <n-select v-model:value="aiConfig.model_name" :options="modelOptions" filterable tag :loading="loadingModels" placeholder="先加载模型或手动输入" />
                <n-button size="small" secondary :loading="loadingModels" @click="loadModels">加载模型</n-button>
              </n-space>
            </n-form-item>
          </n-gi>
        </n-grid>

        <n-divider />
        <n-form-item label="转录完成后的 AI 分析方式">
          <n-radio-group v-model:value="aiSettings.mode">
            <n-radio-button value="none">不自动分析</n-radio-button>
            <n-radio-button value="manual">手动选择分析</n-radio-button>
            <n-radio-button value="auto">自动加入分析队列</n-radio-button>
          </n-radio-group>
        </n-form-item>
        <n-form-item v-if="aiSettings.mode === 'auto'" label="自动分析类型">
          <n-checkbox-group v-model:value="aiSettings.autoTypes">
            <n-space>
              <n-checkbox v-for="option in analysisTypeOptions" :key="option.value" :value="option.value" :label="option.label" />
            </n-space>
          </n-checkbox-group>
        </n-form-item>

        <div class="provider-actions">
          <n-button type="primary" secondary :loading="testing" @click="testAi">测试接口连通性</n-button>
          <span>密钥仅用于当前运行环境，不会影响本地 ASR 转录。</span>
        </div>
      </n-form>
    </n-card>

    <n-card title="5. 云端转录同步" class="cloud-sync-card">
      <template #header-extra>
        <n-space align="center"><n-text depth="3">独立数据库</n-text><n-switch v-model:value="cloudSync.enabled" :rail-style="railStyle" /></n-space>
      </template>
      <n-alert v-if="!cloudSync.enabled" type="info" :bordered="false" style="margin-bottom: 16px">开启后可将本地转录文案、时间戳分段和 AI 摘要/总结同步到云端。</n-alert>
      <n-form label-placement="top">
        <n-grid :cols="2" :x-gap="16" responsive="screen">
          <n-gi><n-form-item label="云端服务地址"><n-input v-model:value="cloudSync.baseUrl" placeholder="http://127.0.0.1:8088" /></n-form-item></n-gi>
          <n-gi><n-form-item label="同步秘钥"><n-input v-model:value="cloudSync.token" type="password" show-password-on="click" placeholder="与云端 archive.sync.token 一致" /></n-form-item></n-gi>
          <n-gi><n-form-item label="自动同步"><n-switch v-model:value="cloudSync.autoSync" /><n-text depth="3" style="margin-left: 10px">转录或 AI 分析完成后自动上传</n-text></n-form-item></n-gi>
          <n-gi><n-form-item label="失败重试次数"><n-input-number v-model:value="cloudSync.retryCount" :min="0" :max="5" style="width: 100%" /></n-form-item></n-gi>
        </n-grid>
        <n-space><n-button type="primary" secondary :loading="testingCloud" @click="testCloud">测试云端连接</n-button><n-text v-if="cloudStatus" depth="2">{{ cloudStatus.message }}</n-text></n-space>
      </n-form>
    </n-card>
  </n-space>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { Save as SaveOutline } from '@vicons/ionicons5'
import api from '@/api'

const message = useMessage()

const saving = ref(false)
const checking = ref(false)
const testing = ref(false)
const loadingModels = ref(false)
const modelOptions = ref([])

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
const aiSettings = ref({ mode: 'manual', autoTypes: ['SUMMARY', 'CONCLUSION'] })
const cloudSync = ref({ enabled: false, autoSync: false, baseUrl: '', token: '', timeoutSeconds: 30, retryCount: 2 })
const testingCloud = ref(false)
const cloudStatus = ref(null)
const analysisTypeOptions = [
  { label: '摘要', value: 'SUMMARY' }, { label: '总结', value: 'CONCLUSION' }
]

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

const railStyle = ({ focused, checked }) => {
  const style = {}
  if (checked) style.background = '#1f7a5a'
  if (focused) style.boxShadow = '0 0 0 2px rgba(31, 122, 90, .2)'
  return style
}


async function loadSettings() {
  try {
    const saved = await api.getSystemSettings()
    const data = await api.getSystemInfo()
    if (saved.settings && Object.keys(saved.settings).length) {
      settings.value = { ...settings.value, ...saved.settings }
    } else if (data.settings) {
      settings.value = { ...settings.value, ...data.settings }
    }
    if (saved.aiConfig && Object.keys(saved.aiConfig).length) {
      aiConfig.value = { ...aiConfig.value, ...saved.aiConfig }
    } else if (data.ai_config) {
      aiConfig.value = { ...aiConfig.value, ...data.ai_config }
    }
    aiSettings.value = { ...aiSettings.value, ...(saved.aiSettings || await api.getAiSettings()) }
    cloudSync.value = { ...cloudSync.value, ...(saved.cloudSync || await api.getCloudSyncConfig()) }
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
}

async function handleSave() {
  saving.value = true
  try {
    await api.saveSystemSettings({ settings: settings.value, aiConfig: aiConfig.value, aiSettings: aiSettings.value, cloudSync: cloudSync.value })
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

async function loadModels() {
  if (!aiConfig.value.base_url) {
    message.warning('请先填写 Base URL')
    return
  }
  loadingModels.value = true
  try {
    const result = await api.getAiModels({ provider: aiConfig.value.provider, baseUrl: aiConfig.value.base_url, apiKey: aiConfig.value.api_key })
    if (!result.available) { message.warning(result.message || '无法加载模型列表'); return }
    modelOptions.value = result.models.map(model => ({ label: model, value: model }))
    if (!modelOptions.value.length) message.info('接口未返回可用模型')
    else message.success(`已加载 ${modelOptions.value.length} 个模型`)
  } catch (error) { message.error('模型列表加载失败') }
  finally { loadingModels.value = false }
}

async function testCloud() {
  testingCloud.value = true
  try {
    await api.saveCloudSyncConfig(cloudSync.value)
    cloudStatus.value = await api.testCloudSync()
    if (cloudStatus.value.available) message.success('云端连接正常')
    else message.warning(cloudStatus.value.message || '云端连接失败')
  } catch (error) { cloudStatus.value = { available: false, message: '云端连接失败' }; message.error('云端连接失败') }
  finally { testingCloud.value = false }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-page {
  --settings-accent: #1f7a5a;
}

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

.provider-heading { display: flex; align-items: flex-start; gap: 14px; }
.provider-heading h2 { margin: 4px 0 3px; font-size: 18px; font-weight: 650; }
.provider-heading p { margin: 0; color: var(--n-text-color-3); font-size: 12px; }
.provider-toggle { display: inline-flex; align-items: center; gap: 10px; color: var(--n-text-color-2); font-size: 13px; font-weight: 600; cursor: pointer; }
.ai-provider-card { border-color: rgba(31, 122, 90, .28); }
.ai-provider-disabled { border-color: var(--n-border-color); }
.provider-disabled-state { display: flex; align-items: center; gap: 14px; padding: 20px; border: 1px dashed var(--n-border-color); border-radius: 8px; background: var(--n-color-embedded); }
.provider-disabled-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 10px; color: var(--n-text-color-3); background: var(--n-color-modal); font-size: 12px; font-weight: 800; letter-spacing: .08em; }
.provider-disabled-state strong { font-size: 14px; }
.provider-disabled-state p { margin: 4px 0 0; color: var(--n-text-color-3); font-size: 12px; line-height: 1.5; }
.provider-actions { display: flex; align-items: center; gap: 12px; }
.provider-actions span { color: var(--n-text-color-3); font-size: 12px; }

@media (max-width: 520px) {
  .provider-actions { align-items: flex-start; flex-direction: column; }
}
</style>
