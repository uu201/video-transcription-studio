import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAiAnalysisStore = defineStore('aiAnalysis', () => {
  const tasks = ref([])
  const loading = ref(false)

  const stats = computed(() => ({
    queued: tasks.value.filter(task => task.status === 'QUEUED').length,
    running: tasks.value.filter(task => task.status === 'RUNNING').length,
    succeeded: tasks.value.filter(task => task.status === 'SUCCEEDED').length,
    failed: tasks.value.filter(task => task.status === 'FAILED').length,
    canceled: tasks.value.filter(task => task.status === 'CANCELED').length
  }))

  async function fetchTasks(params) {
    loading.value = true
    try { tasks.value = await api.getAiTasks(params) } finally { loading.value = false }
  }

  async function startTask(id) { await api.startAiTask(id); await fetchTasks() }
  async function pauseTask(id) { await api.pauseAiTask(id); await fetchTasks() }
  async function cancelTask(id) { await api.cancelAiTask(id); await fetchTasks() }

  function mergeRealtimeTask(update) {
    const index = tasks.value.findIndex(task => task.id === update.taskId)
    if (index < 0) return fetchTasks()
    const current = tasks.value[index]
    if (update.updatedAt && current.updatedAt && Date.parse(update.updatedAt) < Date.parse(current.updatedAt)) return
    tasks.value[index] = { ...current, ...update, id: current.id, updatedAt: update.updatedAt || current.updatedAt }
  }

  function removeRealtimeTask(id) { tasks.value = tasks.value.filter(task => task.id !== id) }

  return { tasks, loading, stats, fetchTasks, mergeRealtimeTask, removeRealtimeTask, startTask, pauseTask, cancelTask }
})
