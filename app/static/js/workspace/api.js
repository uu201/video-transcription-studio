/* API 请求封装模块 */
(function(window) {
  'use strict';

  async function request(url, options) {
    const response = await fetch(url, options);
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      throw new Error((data && (data.detail || data.message)) || "请求失败");
    }
    return data;
  }

  // API 方法集合
  const api = {
    // 扫描源相关
    sources: {
      list: () => request("/api/scan-sources"),
      create: (data) => request("/api/scan-sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      }),
      update: (id, data) => request(`/api/scan-sources/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      }),
      delete: (id) => request(`/api/scan-sources/${id}`, { method: "DELETE" }),
      scan: (id) => request(`/api/scan-sources/${id}/scan`, { method: "POST" }),
      media: (id, availableOnly = true) =>
        request(`/api/scan-sources/${id}/media?available_only=${availableOnly}`)
    },

    // 任务相关
    tasks: {
      list: (limit = 500) => request(`/api/tasks?limit=${limit}`),
      get: (id) => request(`/api/tasks/${id}`),
      create: (mediaFileId) => request("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mediaFileId })
      }),
      batchCreate: (mediaFileIds) => request("/api/tasks/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mediaFileIds })
      }),
      retry: (id) => request(`/api/tasks/${id}/retry`, { method: "POST" }),
      cancel: (id) => request(`/api/tasks/${id}/cancel`, { method: "POST" }),
      delete: (id) => request(`/api/tasks/${id}`, { method: "DELETE" }),
      transcript: (id) => request(`/api/tasks/${id}/transcript`),
      segments: (id) => request(`/api/tasks/${id}/segments`)
    },

    // 系统相关
    system: {
      info: () => request("/api/system/info"),
      environment: () => request("/api/system/environment"),
      checkMediaTools: () => request("/api/system/check-media-tools", { method: "POST" })
    }
  };

  // 导出到全局
  window.AppAPI = api;

})(window);
