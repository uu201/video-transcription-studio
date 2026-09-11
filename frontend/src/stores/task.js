import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const loading = ref(false)

  const taskStats = computed(() => {
    return {
      pending: tasks.value.filter(t => t.status === 'QUEUED').length,
      processing: tasks.value.filter(t => t.status === 'RUNNING').length,
      completed: tasks.value.filter(t => t.status === 'SUCCEEDED').length,
      failed: tasks.value.filter(t => t.status === 'FAILED').length
    }
  })

  async function fetchTasks() {
    loading.value = true
    try {
      const data = await api.getTasks()
      tasks.value = data
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
    taskStats,
    fetchTasks,
    getTaskDetail,
    retryTask,
    cancelTask,
    deleteTask
  }
})
