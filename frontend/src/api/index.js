import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

request.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
  // 系统信息
  getSystemInfo() {
    return request.get('/system/info')
  },

  getEnvironment(force = false) {
    return request.get('/system/environment', { params: { force } })
  },

  checkMediaTools() {
    return request.post('/system/check-media-tools')
  },

  // 扫描源
  getSources() {
    return request.get('/scan-sources')
  },

  createSource(data) {
    return request.post('/scan-sources', data)
  },

  updateSource(id, data) {
    return request.put(`/scan-sources/${id}`, data)
  },

  deleteSource(id) {
    return request.delete(`/scan-sources/${id}`)
  },

  scanSource(id) {
    return request.post(`/scan-sources/${id}/scan`)
  },

  // 任务
  getTasks(params) {
    return request.get('/tasks', { params })
  },

  getTaskDetail(id) {
    return request.get(`/tasks/${id}`)
  },
  getAiSettings() { return request.get('/system/ai-settings') },
  saveAiSettings(data) { return request.put('/system/ai-settings', data) },
  getSystemSettings() { return request.get('/system/settings') },
  saveSystemSettings(data) { return request.put('/system/settings', data) },
  getAiModels(data) { return request.post('/system/ai-models', data) },

  getTranscript(id) {
    return request.get(`/tasks/${id}/transcript`)
  },

  getTaskSegments(id) {
    return request.get(`/tasks/${id}/segments`)
  },

  getResults(params) {
    return request.get('/results', { params })
  },
  deleteResults(ids) {
    return request.delete('/results', { data: { ids } })
  },

  getTaskAnalyses(id) {
    return request.get(`/tasks/${id}/analyses`)
  },

  getAiTasks(params) {
    return request.get('/ai/tasks', { params })
  },
  getAiTask(id) { return request.get(`/ai/tasks/${id}`) },

  createAiAnalysis(transcriptId, data) {
    return request.post(`/ai/transcripts/${transcriptId}`, data)
  },

  retryAiTask(id) {
    return request.post(`/ai/tasks/${id}/retry`)
  },
  reanalyzeAiTask(id) { return request.post(`/ai/tasks/${id}/reanalyze`) },

  cancelAiTask(id) {
    return request.post(`/ai/tasks/${id}/cancel`)
  },
  deleteAiTask(id) { return request.delete(`/ai/tasks/${id}`) },

  startAiTask(id) {
    return request.post(`/ai/tasks/${id}/start`)
  },

  pauseAiTask(id) {
    return request.post(`/ai/tasks/${id}/pause`)
  },

  createTasks(data) {
    return request.post('/tasks/batch', data)
  },

  retryTask(id) {
    return request.post(`/tasks/${id}/retry`)
  },

  cancelTask(id) {
    return request.post(`/tasks/${id}/cancel`)
  },

  pauseTask(id) {
    return request.post(`/tasks/${id}/pause`)
  },

  resumeTask(id) {
    return request.post(`/tasks/${id}/resume`)
  },

  deleteTask(id) {
    return request.delete(`/tasks/${id}`)
  },

  // 导出
  exportTranscript(taskId, format) {
    return request.get(`/tasks/${taskId}/download`, {
      params: { type: format },
      responseType: 'blob'
    })
  }
}
