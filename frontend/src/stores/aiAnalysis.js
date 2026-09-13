import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useAiAnalysisStore = defineStore('aiAnalysis', () => {
  const tasks = ref([])
  const loading = ref(false)
  let fetchSequence = 0

  const stats = computed(() => ({
    queued: tasks.value.filter(task => task.status === 'QUEUED').length,
    running: tasks.value.filter(task => task.status === 'RUNNING').length,
    paused: tasks.value.filter(task => task.status === 'PAUSED').length,
    succeeded: tasks.value.filter(task => task.status === 'SUCCEEDED').length,
    failed: tasks.value.filter(task => task.status === 'FAILED').length,
    canceled: tasks.value.filter(task => task.status === 'CANCELED').length
  }))

  async function fetchTasks(params) {
    const requestSequence = ++fetchSequence
    loading.value = true
    try {
      const data = await api.getAiTasks(params)
      if (requestSequence !== fetchSequence) return
      const current = new Map(tasks.value.map(task => [task.id, task]))
      tasks.value = data.map(task => {
        const previous = current.get(task.id)
        if (!previous || !previous.updatedAt || !task.updatedAt || Date.parse(task.updatedAt) >= Date.parse(previous.updatedAt)) {
          return { ...previous, ...task }
        }
        return previous
      })
    } catch (error) {
      console.error('Failed to fetch AI tasks:', error)
    } finally {
      if (requestSequence === fetchSequence) loading.value = false
    }
  }

  async function startTask(id) { await api.startAiTask(id); await fetchTasks() }
  async function pauseTask(id) { await api.pauseAiTask(id); await fetchTasks() }
  async function cancelTask(id) { await api.cancelAiTask(id); await fetchTasks() }
  async function retryTask(id) { await api.retryAiTask(id); await fetchTasks() }
  async function reanalyzeTask(id) { await api.reanalyzeAiTask(id); await fetchTasks() }
  async function deleteTask(id) { await api.deleteAiTask(id); removeRealtimeTask(id) }
  async function pauseAllTasks() { const result = await api.pauseAllAiTasks(); await fetchTasks(); return result }
  async function startAllTasks() { const result = await api.startAllAiTasks(); await fetchTasks(); return result }

  function mergeRealtimeTask(update) {
    const index = tasks.value.findIndex(task => task.id === update.taskId)
    if (index < 0) return fetchTasks()
    const current = tasks.value[index]
    const updatedAt = update.updatedAt || update.at
    if (updatedAt && current.updatedAt && Date.parse(updatedAt) < Date.parse(current.updatedAt)) return
    const shouldResetProgress = update.progress !== undefined && ['QUEUED', 'PAUSED'].includes(update.status)
    const nextProgress = update.progress !== undefined
      ? (shouldResetProgress ? Math.max(0, Math.min(100, Number(update.progress) || 0)) : Math.max(Number(current.progress) || 0, Number(update.progress) || 0))
      : current.progress
    tasks.value[index] = {
      ...current,
      ...(update.status ? { status: update.status } : {}),
      ...(update.progress !== undefined ? { progress: nextProgress } : {}),
      ...(update.message !== undefined ? { message: update.message } : {}),
      ...(update.pauseRequested !== undefined ? { pauseRequested: update.pauseRequested } : {}),
      ...(update.cancelRequested !== undefined ? { cancelRequested: update.cancelRequested } : {}),
      ...(update.error !== undefined ? { error: update.error } : {}),
      ...(updatedAt ? { updatedAt } : {})
    }
  }

  function removeRealtimeTask(id) { tasks.value = tasks.value.filter(task => task.id !== id) }

  return { tasks, loading, stats, fetchTasks, mergeRealtimeTask, removeRealtimeTask, startTask, pauseTask, cancelTask, retryTask, reanalyzeTask, deleteTask, pauseAllTasks, startAllTasks }
})
