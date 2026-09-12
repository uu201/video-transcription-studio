import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)
  let fetchSequence = 0

  function replaceRealtimeTasks(incoming) {
    const current = new Map(tasks.value.map(task => [task.id, task]))
    tasks.value = incoming.map(task => ({ ...current.get(task.id), ...task }))
  }

  function mergeRealtimeTask(update) {
    const index = tasks.value.findIndex(task => task.id === update.taskId)
    if (index === -1) {
      fetchTasks({ merge: true })
      return
    }
    const current = tasks.value[index]
    if (update.at && current.updatedAt && Date.parse(update.at) < Date.parse(current.updatedAt)) {
      return
    }
    const nextProgress = update.progress !== undefined
      ? Math.max(Number(current.progress) || 0, Number(update.progress) || 0)
      : current.progress
    tasks.value[index] = {
      ...current,
      ...(update.status ? { status: update.status } : {}),
      ...(update.stage ? { stage: update.stage } : {}),
      ...(update.progress !== undefined ? { progress: nextProgress } : {}),
      ...(update.message !== undefined ? { message: update.message } : {}),
      ...(update.pauseRequested !== undefined ? { pauseRequested: update.pauseRequested } : {}),
      ...(update.cancelRequested !== undefined ? { cancelRequested: update.cancelRequested } : {}),
      ...(update.at ? { updatedAt: update.at } : {}),
      ...(update.error ? { error: update.error } : {})
    }
  }

  function removeRealtimeTask(taskId) {
    tasks.value = tasks.value.filter(task => task.id !== taskId)
  }

  const taskStats = computed(() => {
    return {
      pending: tasks.value.filter(t => t.status === 'QUEUED').length,
      processing: tasks.value.filter(t => t.status === 'RUNNING').length,
      paused: tasks.value.filter(t => t.status === 'PAUSED').length,
      completed: tasks.value.filter(t => t.status === 'SUCCEEDED').length,
      failed: tasks.value.filter(t => t.status === 'FAILED').length,
      canceled: tasks.value.filter(t => t.status === 'CANCELED').length
    }
  })

  async function fetchTasks() {
    const requestSequence = ++fetchSequence
    loading.value = true
    try {
      const data = await api.getTasks()
      if (requestSequence === fetchSequence) {
        const current = new Map(tasks.value.map(task => [task.id, task]))
        tasks.value = data.map(task => {
          const previous = current.get(task.id)
          if (!previous || !previous.updatedAt || !task.updatedAt || Date.parse(task.updatedAt) >= Date.parse(previous.updatedAt)) {
            return { ...previous, ...task }
          }
          return previous
        })
      }
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
    } finally {
      loading.value = false
    }
  }

  async function getTaskDetail(id) {
    try {
      return await api.getTaskDetail(id)
    } catch (error) {
      console.error('Failed to fetch task detail:', error)
      return null
    }
  }

  async function retryTask(id) {
    try {
      await api.retryTask(id)
      await fetchTasks()
    } catch (error) {
      console.error('Failed to retry task:', error)
      throw error
    }
  }

  async function cancelTask(id) {
    try {
      await api.cancelTask(id)
      await fetchTasks()
    } catch (error) {
      console.error('Failed to cancel task:', error)
      throw error
    }
  }

  async function pauseTask(id) {
    try {
      await api.pauseTask(id)
      await fetchTasks()
    } catch (error) {
      console.error('Failed to pause task:', error)
      throw error
    }
  }

  async function resumeTask(id) {
    try {
      await api.resumeTask(id)
      await fetchTasks()
    } catch (error) {
      console.error('Failed to resume task:', error)
      throw error
    }
  }

  async function deleteTask(id) {
    try {
      await api.deleteTask(id)
      await fetchTasks()
    } catch (error) {
      console.error('Failed to delete task:', error)
      throw error
    }
  }

  return {
    tasks,
    loading,
    replaceRealtimeTasks,
    mergeRealtimeTask,
    removeRealtimeTask,
    taskStats,
    fetchTasks,
    getTaskDetail,
    retryTask,
    cancelTask,
    pauseTask,
    resumeTask,
    deleteTask
  }
})
