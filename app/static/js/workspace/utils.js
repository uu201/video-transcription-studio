/* 数据格式化和转换工具 */
(function(window) {
  'use strict';

  // 状态映射
  const statusMap = {
    QUEUED: "pending",
    RUNNING: "processing",
    SUCCEEDED: "completed",
    FAILED: "failed",
    CANCELED: "cancelled"
  };

  const statusLabel = {
    pending: "待处理",
    processing: "处理中",
    completed: "已完成",
    failed: "处理失败",
    cancelled: "已取消"
  };

  // 时间格式化
  function formatTime(value) {
    return value ? String(value).replace("T", " ").slice(0, 19) : "--";
  }

  // 文件大小格式化
  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  }

  // 扫描源数据转换
  function mapSource(item) {
    return {
      ...item,
      path: item.rootPath,
      postAction: item.transferPolicy || "keep",
      lastScanAt: formatTime(item.updatedAt),
      scanning: false
    };
  }

  // 任务数据转换
  function mapTask(item) {
    const status = statusMap[item.status] || String(item.status || "QUEUED").toLowerCase();
    return {
      ...item,
      taskId: "TASK-" + String(item.id).padStart(4, "0"),
      fileName: item.fileName || "未知媒体",
      filePath: item.path || "--",
      fileType: (item.fileName || "file").split(".").pop(),
      status,
      currentPhase: item.stage || item.message || statusLabel[status],
      updatedAt: formatTime(item.updatedAt),
      errorInfo: item.error ? {
        title: item.error.message,
        desc: item.error.detail || item.error.message,
        solution: item.error.retryable ? "检查环境后重试任务。" : "该任务不可重试。",
        cmd: "python -m pip install -r requirements.txt",
        traceback: item.error.detail || ""
      } : null,
      pipeline: [],
      transcript: null,
      segments: []
    };
  }

  // 环境数据转换
  function makeEnvironment(data) {
    const fallback = {
      python: {},
      funasr: {},
      ffmpeg: {},
      ffprobe: {},
      sqlite: {},
      modelDir: {},
      senseVoice: {},
      vad: {},
      cuda: {}
    };

    (data.items || []).forEach((item) => {
      const key = item.key === "database" ? "sqlite" :
                  item.key === "modelDir" ? "modelDir" :
                  item.key === "iic/SenseVoiceSmall" ? "senseVoice" :
                  item.key.indexOf("speech_fsmn") >= 0 ? "vad" : item.key;

      if (!fallback[key]) return;

      fallback[key] = {
        ok: item.status === "ok",
        available: item.status === "ok",
        status: item.value,
        version: item.value,
        path: item.detail,
        device: item.value,
        size: "--",
        progress: item.status === "ok" ? 100 : 0
      };
    });

    return fallback;
  }

  // 导出工具函数
  window.AppUtils = {
    formatTime,
    formatFileSize,
    mapSource,
    mapTask,
    makeEnvironment,
    statusMap,
    statusLabel
  };

})(window);
