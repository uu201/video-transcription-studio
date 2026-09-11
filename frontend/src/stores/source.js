import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'

export const useSourceStore = defineStore('source', () => {
  const sources = ref([])
  const loading = ref(false)

  async function fetchSources() {
    loading.value = true
    try {
      const data = await api.getSources()
      sources.value = data
    } catch (error) {
      console.error('Failed to fetch sources:', error)
    } finally {
      loading.value = false
    }
  }

  async function createSource(sourceData) {
    try {
      const newSource = await api.createSource(sourceData)
      await fetchSources()
      return newSource
    } catch (error) {
      console.error('Failed to create source:', error)
      throw error
    }
  }

  async function updateSource(id, sourceData) {
    try {
      await api.updateSource(id, sourceData)
      await fetchSources()
    } catch (error) {
      console.error('Failed to update source:', error)
      throw error
    }
  }

  async function deleteSource(id) {
    try {
      await api.deleteSource(id)
      await fetchSources()
    } catch (error) {
      console.error('Failed to delete source:', error)
      throw error
    }
  }

  async function scanSource(id) {
    try {
      const result = await api.scanSource(id)
      await fetchSources()
      return result
    } catch (error) {
      console.error('Failed to scan source:', error)
      throw error
    }
  }

  return {
    sources,
    loading,
    fetchSources,
    createSource,
    updateSource,
    deleteSource,
    scanSource
  }
})
