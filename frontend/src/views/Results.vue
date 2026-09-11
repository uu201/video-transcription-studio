<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">转录结果</h1>
        <n-text depth="3">把已完成的转录稿整理成可阅读、可复用的内容资产</n-text>
      </div>
      <n-space align="center">
        <n-tag type="success" size="small">{{ results.length }} 份结果</n-tag>
        <n-button :loading="loading" @click="loadResults">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新结果
        </n-button>
      </n-space>
    </div>

    <n-card size="small" class="result-toolbar">
      <n-input v-model:value="searchKeyword" clearable placeholder="搜索文件名或文案内容..." style="max-width: 420px">
        <template #prefix><n-icon><SearchOutline /></n-icon></template>
      </n-input>
      <n-text depth="3">按完成时间倒序排列</n-text>
    </n-card>

    <n-spin :show="loading">
      <n-empty v-if="filteredResults.length === 0" description="暂无已完成的转录结果">
        <template #extra>
          <n-button type="primary" @click="router.push('/tasks')">查看处理队列</n-button>
        </template>
      </n-empty>

      <section v-else class="shelf" aria-label="转录结果书架">
        <div class="shelf-topline">
          <div>
            <span class="shelf-kicker">TRANSCRIPT LIBRARY</span>
            <h2>内容书架</h2>
          </div>
          <n-text depth="3">点击卡片阅读完整内容</n-text>
        </div>
        <div class="book-grid">
          <button
            v-for="(result, index) in filteredResults"
            :key="result.id"
            class="book-card"
            type="button"
            @click="router.push(`/results/${result.id}`)"
          >
            <div class="book-cover" :class="`cover-${index % 5}`">
              <span class="cover-type">TRANSCRIPT</span>
              <span class="cover-number">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="cover-mark">文</span>
            </div>
            <div class="book-info">
              <strong :title="result.fileName">{{ result.fileName || '未命名媒体' }}</strong>
              <span>{{ formatDateTime(result.finishedAt || result.updatedAt) }}</span>
              <p>{{ previewText(result.cleanText || result.rawText) }}</p>
              <div class="book-meta">
                <span>{{ result.segmentCount || 0 }} 段</span>
                <span v-if="result.analysisCount">AI {{ result.analysisCount }}</span>
                <span v-else class="muted">未分析</span>
              </div>
            </div>
          </button>
        </div>
        <div class="shelf-ledge" aria-hidden="true"></div>
      </section>
    </n-spin>
  </n-space>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag, useMessage } from 'naive-ui'
import { Refresh as RefreshOutline, Search as SearchOutline } from '@vicons/ionicons5'
import api from '@/api'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const loading = ref(false)
const results = ref([])
const searchKeyword = ref('')

const filteredResults = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return results.value
  return results.value.filter(result =>
    [result.fileName, result.cleanText, result.rawText].some(value => String(value || '').toLowerCase().includes(keyword))
  )
})

function previewText(value) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text ? `${text.slice(0, 86)}${text.length > 86 ? '…' : ''}` : '暂无可预览文案'
}

async function loadResults() {
  loading.value = true
  try {
    results.value = await api.getResults()
  } catch (error) {
    results.value = []
    message.error('加载转录结果失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

onMounted(loadResults)
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
  margin-bottom: 4px;
  font-size: 24px;
  font-weight: 600;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.shelf {
  position: relative;
  padding: 22px 22px 34px;
  border: 1px solid var(--n-border-color);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(217, 243, 107, 0.08), transparent 34%);
}

.shelf-topline {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 24px;
}

.shelf-kicker {
  color: #7c8d1a;
  font-size: 11px;
  letter-spacing: 0.12em;
  font-weight: 700;
}

.shelf-topline h2 {
  margin: 4px 0 0;
  font-size: 20px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 22px 18px;
}

.book-card {
  min-width: 0;
  padding: 0;
  border: 0;
  color: inherit;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: transform 160ms ease;
}

.book-card:hover,
.book-card:focus-visible {
  transform: translateY(-5px);
}

.book-card:focus-visible {
  outline: 2px solid var(--n-primary-color);
  outline-offset: 5px;
}

.book-cover {
  position: relative;
  display: flex;
  min-height: 190px;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 18px;
  border-radius: 6px 9px 9px 6px;
  color: #fff;
  box-shadow: 8px 10px 0 rgba(0, 0, 0, 0.1), 0 14px 26px rgba(22, 28, 10, 0.13);
}

.book-cover::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 10px;
  width: 2px;
  background: rgba(255, 255, 255, 0.28);
  content: '';
}

.cover-0 { background: #536b32; }
.cover-1 { background: #914f35; }
.cover-2 { background: #345c68; }
.cover-3 { background: #705780; }
.cover-4 { background: #7a6131; }

.cover-type,
.cover-number {
  position: relative;
  font-size: 10px;
  letter-spacing: 0.1em;
  opacity: 0.8;
}

.cover-number {
  align-self: flex-end;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 13px;
}

.cover-mark {
  position: relative;
  align-self: center;
  font-family: Georgia, serif;
  font-size: 72px;
  font-weight: 700;
  line-height: 1;
  opacity: 0.88;
}

.book-info {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
  padding: 14px 4px 0;
}

.book-info strong,
.book-info span,
.book-info p {
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-info strong {
  white-space: nowrap;
  font-size: 14px;
}

.book-info > span {
  color: var(--n-text-color-3);
  font-size: 11px;
}

.book-info p {
  display: -webkit-box;
  min-height: 36px;
  margin: 0;
  color: var(--n-text-color-2);
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.book-meta {
  display: flex;
  gap: 10px;
  color: var(--n-primary-color);
  font-size: 11px;
}

.book-meta .muted { color: var(--n-text-color-3); }

.shelf-ledge {
  height: 8px;
  margin: 28px -6px -20px;
  border-radius: 2px;
  background: var(--n-border-color);
  box-shadow: 0 5px 0 rgba(0, 0, 0, 0.08);
}

@media (max-width: 620px) {
  .shelf { padding: 16px 14px 28px; }
  .shelf-topline { align-items: flex-start; flex-direction: column; }
  .book-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 12px; }
  .book-cover { min-height: 150px; padding: 14px; }
  .cover-mark { font-size: 54px; }
}
</style>
