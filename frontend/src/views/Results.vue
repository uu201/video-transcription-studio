<template>
  <n-space vertical :size="24">
    <div class="page-header">
      <div>
        <h1 class="page-title">转录成果</h1>
        <n-text depth="3">浏览、导出和管理已完成的转录内容</n-text>
      </div>
      <n-space align="center">
        <n-tag type="success" size="small">{{ results.length }} 份结果</n-tag>
        <n-button secondary @click="router.push('/sources')">
          <template #icon><n-icon><ScanOutline /></n-icon></template>
          扫描素材
        </n-button>
        <n-button type="error" secondary :disabled="selectedIds.length === 0" @click="deleteSelected">
          <template #icon><n-icon><TrashOutline /></n-icon></template>
          删除选中{{ selectedIds.length ? ` (${selectedIds.length})` : '' }}
        </n-button>
        <n-button :loading="loading" @click="loadResults">
          <template #icon><n-icon><RefreshOutline /></n-icon></template>
          刷新结果
        </n-button>
      </n-space>
    </div>

      <div class="result-toolbar">
        <n-input v-model:value="searchKeyword" clearable placeholder="搜索文件名或文案内容..." class="search-input">
          <template #prefix><n-icon><SearchOutline /></n-icon></template>
        </n-input>
        <n-checkbox :checked="allVisibleSelected" @update:checked="toggleSelectAll">全选当前结果</n-checkbox>
        <n-text depth="3" class="sort-hint">删除结果后，源文件仍保留，可从素材来源重新扫描处理</n-text>
      </div>

    <n-spin :show="loading">
      <n-empty v-if="filteredResults.length === 0" description="暂无已完成的转录结果">
        <template #extra>
          <n-button type="primary" @click="router.push('/tasks')">查看处理队列</n-button>
        </template>
      </n-empty>

      <section v-else class="shelf" aria-label="转录结果书架">
        <div class="shelf-topline">
          <h2>成果列表</h2>
          <n-text depth="3">点击卡片阅读完整内容</n-text>
        </div>
        <div class="book-grid">
          <article
            v-for="(result, index) in filteredResults"
            :key="result.id"
            class="book-card"
          >
            <n-checkbox
              class="book-select"
              :checked="selectedIds.includes(result.id)"
              @click.stop
              @update:checked="checked => toggleSelection(result.id, checked)"
            />
            <button class="book-card-content" type="button" @click="router.push(`/results/${result.id}`)">
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
          </article>
        </div>
        <div class="shelf-ledge" aria-hidden="true"></div>
      </section>
    </n-spin>
  </n-space>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon, NTag, useDialog, useMessage } from 'naive-ui'
import { Refresh as RefreshOutline, Search as SearchOutline, Scan as ScanOutline, Trash as TrashOutline } from '@vicons/ionicons5'
import api from '@/api'
import { formatDateTime } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()
const loading = ref(false)
const results = ref([])
const searchKeyword = ref('')
const selectedIds = ref([])

const filteredResults = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return results.value
  return results.value.filter(result =>
    [result.fileName, result.cleanText, result.rawText].some(value => String(value || '').toLowerCase().includes(keyword))
  )
})
const allVisibleSelected = computed(() => filteredResults.value.length > 0 && filteredResults.value.every(result => selectedIds.value.includes(result.id)))

function toggleSelection(id, checked) {
  selectedIds.value = checked
    ? [...new Set([...selectedIds.value, id])]
    : selectedIds.value.filter(value => value !== id)
}

function toggleSelectAll(checked) {
  const visibleIds = filteredResults.value.map(result => result.id)
  selectedIds.value = checked
    ? [...new Set([...selectedIds.value, ...visibleIds])]
    : selectedIds.value.filter(id => !visibleIds.includes(id))
}

function previewText(value) {
  const text = String(value || '').replace(/\s+/g, ' ').trim()
  return text ? `${text.slice(0, 86)}${text.length > 86 ? '…' : ''}` : '暂无可预览文案'
}

async function loadResults() {
  loading.value = true
  try {
    results.value = await api.getResults()
    selectedIds.value = selectedIds.value.filter(id => results.value.some(result => result.id === id))
  } catch (error) {
    results.value = []
    message.error('加载转录结果失败，请检查后端服务')
  } finally {
    loading.value = false
  }
}

function deleteSelected() {
  if (!selectedIds.value.length) return
  dialog.warning({
    title: '删除转录结果',
    content: `确定删除选中的 ${selectedIds.value.length} 份转录结果吗？源视频文件不会被删除，之后可以从素材来源重新扫描处理。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value = true
      try {
        const result = await api.deleteResults(selectedIds.value)
        selectedIds.value = []
        await loadResults()
        message.success(`已删除 ${result.deleted} 份结果，可重新扫描源文件处理`)
      } catch (error) {
        message.error(error?.response?.data?.detail || '删除转录结果失败')
      } finally {
        loading.value = false
      }
    }
  })
}

onMounted(loadResults)
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.page-title {
  margin-bottom: 6px;
  font-size: 28px;
  font-weight: 600;
  line-height: 1.2;
}

.result-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  padding: 16px 20px;
  border-radius: 10px;
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.search-input {
  flex: 1;
  max-width: 480px;
  min-width: 240px;
}

.sort-hint {
  font-size: 13px;
  white-space: nowrap;
}

.shelf {
  position: relative;
  padding: 32px 28px 40px;
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  background: linear-gradient(180deg, rgba(217, 243, 107, 0.06), transparent 40%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.shelf-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
}

.shelf-topline h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--n-text-color-1);
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 24px 20px;
}

.book-card {
  position: relative;
  min-width: 0;
}

.book-card-content {
  display: block;
  width: 100%;
  padding: 0;
  border: 0;
  color: inherit;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: transform 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.book-card-content:hover {
  transform: translateY(-6px);
}

.book-card-content:active {
  transform: translateY(-3px);
  transition-duration: 100ms;
}

.book-card-content:focus-visible {
  outline: 2px solid var(--n-primary-color);
  outline-offset: 6px;
  border-radius: 8px;
}

.book-select {
  position: absolute;
  z-index: 2;
  top: 10px;
  left: 10px;
  padding: 5px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.88);
}

.book-cover {
  position: relative;
  display: flex;
  min-height: 180px;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 18px;
  border-radius: 8px 10px 10px 8px;
  color: #fff;
  box-shadow:
    5px 7px 0 rgba(0, 0, 0, 0.08),
    0 10px 20px rgba(22, 28, 10, 0.12),
    0 3px 6px rgba(0, 0, 0, 0.08);
  transition: box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.book-card-content:hover .book-cover {
  box-shadow:
    7px 9px 0 rgba(0, 0, 0, 0.1),
    0 14px 28px rgba(22, 28, 10, 0.16),
    0 5px 10px rgba(0, 0, 0, 0.1);
}

.book-cover::before {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 12px;
  width: 2px;
  background: rgba(255, 255, 255, 0.32);
  content: '';
}

.cover-0 { background: linear-gradient(135deg, #5a7438 0%, #4a5f2e 100%); }
.cover-1 { background: linear-gradient(135deg, #9a5640 0%, #7d4532 100%); }
.cover-2 { background: linear-gradient(135deg, #3a6575 0%, #2d5160 100%); }
.cover-3 { background: linear-gradient(135deg, #7b5f8a 0%, #624d70 100%); }
.cover-4 { background: linear-gradient(135deg, #856a38 0%, #6b562e 100%); }

.cover-type,
.cover-number {
  position: relative;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.85;
}

.cover-number {
  align-self: flex-end;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 14px;
  font-weight: 500;
}

.cover-mark {
  position: relative;
  align-self: center;
  font-family: Georgia, 'Noto Serif SC', serif;
  font-size: 68px;
  font-weight: 700;
  line-height: 1;
  opacity: 0.9;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.book-info {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
  padding: 16px 4px 0;
}

.book-info strong,
.book-info span,
.book-info p {
  overflow: hidden;
  text-overflow: ellipsis;
}

.book-info strong {
  white-space: nowrap;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}

.book-info > span {
  color: var(--n-text-color-3);
  font-size: 12px;
}

.book-info p {
  display: -webkit-box;
  min-height: 40px;
  margin: 0;
  color: var(--n-text-color-2);
  font-size: 13px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.book-meta {
  display: flex;
  gap: 12px;
  color: var(--n-primary-color);
  font-size: 12px;
  font-weight: 500;
}

.book-meta .muted {
  color: var(--n-text-color-3);
  font-weight: 400;
}

.shelf-ledge {
  height: 10px;
  margin: 32px -8px -24px;
  border-radius: 3px;
  background: linear-gradient(180deg, var(--n-border-color) 0%, rgba(0, 0, 0, 0.05) 100%);
  box-shadow: 0 6px 0 rgba(0, 0, 0, 0.06);
}

@media (max-width: 768px) {
  .page-title {
    font-size: 24px;
  }

  .result-toolbar {
    padding: 14px 16px;
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    max-width: 100%;
  }

  .sort-hint {
    text-align: center;
  }

  .shelf {
    padding: 24px 20px 32px;
  }

  .shelf-topline {
    align-items: flex-start;
    flex-direction: column;
    margin-bottom: 20px;
  }

  .book-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 20px 16px;
  }

  .book-cover {
    min-height: 160px;
    padding: 16px;
  }

  .cover-mark {
    font-size: 58px;
  }

  .book-info {
    gap: 6px;
    padding: 12px 4px 0;
  }

  .book-info strong {
    font-size: 14px;
  }

  .book-info p {
    font-size: 12px;
    min-height: 36px;
  }
}

@media (max-width: 480px) {
  .result-toolbar {
    padding: 12px 14px;
  }

  .shelf {
    padding: 20px 16px 28px;
  }

  .book-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px 12px;
  }

  .book-cover {
    min-height: 140px;
    padding: 14px;
  }

  .cover-mark {
    font-size: 50px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .book-card-content,
  .book-cover {
    transition: none;
  }

  .book-card-content:hover {
    transform: none;
  }
}
</style>
