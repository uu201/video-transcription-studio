/* 原型工作台的真实数据层：Vue 负责状态，FastAPI 负责持久化。 */
(function () {
  const { createApp, ref, computed, onMounted } = Vue;
  const { ElMessage, ElMessageBox } = ElementPlus;
  const initial = window.__INITIAL_STATE__ || { tab: "overview", taskId: null };

  // 将后端枚举转换为原型使用的英文小写状态。
  const statusMap = { QUEUED: "pending", RUNNING: "processing", SUCCEEDED: "completed", FAILED: "failed", CANCELED: "cancelled" };
  const reverseStatus = { pending: "QUEUED", processing: "RUNNING", completed: "SUCCEEDED", failed: "FAILED", cancelled: "CANCELED" };
  const statusLabel = { pending: "待处理", processing: "处理中", completed: "已完成", failed: "处理失败", cancelled: "已取消" };

  async function request(url, options) {
    const response = await fetch(url, options);
    const data = response.status === 204 ? null : await response.json();
    if (!response.ok) throw new Error((data && (data.detail || data.message)) || "请求失败");
    return data;
  }

  function formatTime(value) {
    return value ? String(value).replace("T", " ").slice(0, 19) : "--";
  }

  function mapSource(item) {
    return { ...item, path: item.rootPath, postAction: item.transferPolicy || "keep", lastScanAt: formatTime(item.updatedAt), scanning: false };
  }

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
      errorInfo: item.error ? { title: item.error.message, desc: item.error.detail || item.error.message, solution: item.error.retryable ? "检查环境后重试任务。" : "该任务不可重试。", cmd: "python -m pip install -r requirements.txt", traceback: item.error.detail || "" } : null,
      pipeline: [],
      transcript: null,
      segments: [],
    };
  }

  function makeEnvironment(data) {
    const fallback = { python: {}, funasr: {}, ffmpeg: {}, ffprobe: {}, sqlite: {}, modelDir: {}, senseVoice: {}, vad: {}, cuda: {} };
    (data.items || []).forEach((item) => {
      const key = item.key === "database" ? "sqlite" : item.key === "modelDir" ? "modelDir" : item.key === "iic/SenseVoiceSmall" ? "senseVoice" : item.key.indexOf("speech_fsmn") >= 0 ? "vad" : item.key;
      if (!fallback[key]) return;
      fallback[key] = { ok: item.status === "ok", available: item.status === "ok", status: item.value, version: item.value, path: item.detail, device: item.value, size: "--", progress: item.status === "ok" ? 100 : 0 };
    });
    return fallback;
  }

  const app = createApp({
    setup() {
      const currentTab = ref(initial.tab || "overview");
      const currentTaskId = ref(initial.taskId);
      const isDarkTheme = ref(localStorage.getItem("transcriber_dark_theme") !== "false");
      const scanSources = ref([]);
      const tasks = ref([]);
      const currentTask = ref(null);
      const environment = ref({ overall: "attention", checkedAt: "--", items: [] });
      const envData = ref(makeEnvironment({ items: [] }));
      const envOverallReady = ref(false);
      const envLastCheckTime = ref("尚未检测");
      const isEnvChecking = ref(false);
      const isScanningSource = ref(false);
      const isCheckingMediaTools = ref(false);
      const isTestingAi = ref(false);
      const editSourceDialogVisible = ref(false);
      const editingSource = ref(null);
      const fileSelectionDialogVisible = ref(false);
      const scannedFiles = ref([]);
      const selectedFileIds = ref([]);
      const currentScanSource = ref(null);
      const taskSearchKeyword = ref("");

      function handleFileSelectionChange(selection) {
        selectedFileIds.value = selection.map(file => file.id);
      }
      const taskFilterStatus = ref("all");
      const activeTextTab = ref("cleaned");
      const selectedAiAction = ref("detailedSummary");
      const isAiAnalyzing = ref(false);
      const aiProgress = ref(0);
      const sourceForm = ref({ name: "", path: "", recursive: true, stableWaitSeconds: 5, autoScan: false, postAction: "keep" });
      const settings = ref({ asrDevice: "cpu", asrLanguage: "auto", batchSeconds: 60, maxSegmentSeconds: 30, ffmpegPath: "", ffprobePath: "", modelDirPath: "" });
      const aiConfig = ref({ enabled: false, provider: "openai", baseUrl: "", apiKey: "", modelName: "" });

      const breadcrumbTitle = computed(() => ({ overview: "内容处理总览", sources: "扫描源配置", tasks: "处理任务队列", "task-detail": "任务详情诊断", settings: "系统环境设置" }[currentTab.value] || "工作台"));
      const taskStats = computed(() => tasks.value.reduce((result, task) => { result[task.status] = (result[task.status] || 0) + 1; return result; }, { pending: 0, processing: 0, completed: 0, failed: 0, cancelled: 0 }));
      const filteredTasks = computed(() => tasks.value.filter((task) => {
        const keyword = taskSearchKeyword.value.trim().toLowerCase();
        return (taskFilterStatus.value === "all" || task.status === taskFilterStatus.value) && (!keyword || [task.taskId, task.fileName, task.filePath].join(" ").toLowerCase().includes(keyword));
      }));

      async function loadEnvironment() {
        isEnvChecking.value = true;
        try {
          const data = await request("/api/system/environment");
          environment.value = data; envData.value = makeEnvironment(data); envOverallReady.value = data.overall === "ok"; envLastCheckTime.value = formatTime(data.checkedAt);
        } catch (error) { ElMessage.error(error.message); } finally { isEnvChecking.value = false; }
      }

      async function loadSources() { scanSources.value = (await request("/api/scan-sources")).map(mapSource); }
      async function loadTasks() { tasks.value = (await request("/api/tasks?limit=500")).map(mapTask); }
      async function loadTaskDetail(task) {
        const data = await request("/api/tasks/" + task.id);
        const target = mapTask(data);
        target.pipeline = (data.events || []).map((event) => ({ name: event.stage, status: event.level === "ERROR" ? "error" : "done", time: formatTime(event.createdAt), desc: event.message }));
        try { target.transcript = await request("/api/tasks/" + task.id + "/transcript"); } catch (_) { target.transcript = null; }
        try { target.segments = (await request("/api/tasks/" + task.id + "/segments")).map((segment) => ({ ...segment, id: segment.sequence, start: Number(segment.start || 0).toFixed(3), end: Number(segment.end || 0).toFixed(3), speaker: segment.speaker || "--", confidence: segment.confidence || 0 })); } catch (_) { target.segments = []; }
        const index = tasks.value.findIndex((item) => item.id === task.id); if (index >= 0) tasks.value[index] = target;
        currentTask.value = target;
      }
      async function refreshAll() { await Promise.all([loadSources(), loadTasks(), loadEnvironment()]); if (currentTaskId.value) { const task = tasks.value.find((item) => item.id === Number(currentTaskId.value)); if (task) await loadTaskDetail(task); } }

      function applyTheme() { document.body.classList.toggle("light-theme", !isDarkTheme.value); localStorage.setItem("transcriber_dark_theme", String(isDarkTheme.value)); }
      function toggleTheme() { isDarkTheme.value = !isDarkTheme.value; applyTheme(); }
      function switchTab(tab) { currentTab.value = tab; if (tab === "overview") loadEnvironment(); if (tab === "sources") loadSources(); if (tab === "tasks") loadTasks(); }
      function getStatusClass(status) { return "status-tag status-" + status; }
      function getStatusLabel(status) { return statusLabel[status] || status; }
      function openTaskDetail(task) { currentTaskId.value = task.id; currentTab.value = "task-detail"; loadTaskDetail(task); }

      async function handleSaveAndScan() {
        if (!sourceForm.value.name || !sourceForm.value.path) return ElMessage.warning("请填写扫描源名称和目录绝对路径");
        isScanningSource.value = true;
        try {
          const source = await request("/api/scan-sources", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: sourceForm.value.name, rootPath: sourceForm.value.path, recursive: sourceForm.value.recursive, stableWaitSeconds: sourceForm.value.stableWaitSeconds, autoScan: sourceForm.value.autoScan, transferPolicy: sourceForm.value.postAction }) });
          const result = await request("/api/scan-sources/" + source.id + "/scan", { method: "POST" });
          ElMessage.success("扫描完成：发现 " + result.discovered + " 个文件，新增 " + result.created + " 条媒体记录");
          sourceForm.value.name = "";
          sourceForm.value.path = "";
          await loadSources();
          await showFileSelection(source);
        } catch (error) { ElMessage.error(error.message); } finally { isScanningSource.value = false; }
      }
      async function triggerScan(source) {
        source.scanning = true;
        try {
          const result = await request("/api/scan-sources/" + source.id + "/scan", { method: "POST" });
          ElMessage.success("扫描完成：发现 " + result.discovered + " 个文件，新增 " + result.created + " 条媒体记录");
          await loadSources();
          await showFileSelection(source);
        } catch (error) { ElMessage.error(error.message); } finally { source.scanning = false; }
      }
      async function showFileSelection(source) {
        try {
          const files = await request("/api/scan-sources/" + source.id + "/media?available_only=true");
          if (files.length === 0) {
            ElMessage.info("未发现新的媒体文件");
            await refreshAll();
            return;
          }
          scannedFiles.value = files.map(file => ({
            ...file,
            sizeDisplay: formatFileSize(file.sizeBytes),
            modifiedDisplay: new Date(file.modifiedAt).toLocaleString('zh-CN')
          }));
          selectedFileIds.value = files.map(f => f.id);
          currentScanSource.value = source;
          fileSelectionDialogVisible.value = true;
        } catch (error) {
          ElMessage.error(error.message);
        }
      }
      function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
      }
      async function createTasksFromSelection() {
        if (selectedFileIds.value.length === 0) return ElMessage.warning("请至少选择一个文件");
        try {
          const result = await request("/api/tasks/batch", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mediaFileIds: selectedFileIds.value }) });
          ElMessage.success("成功创建 " + result.created + " 个任务");
          fileSelectionDialogVisible.value = false;
          await refreshAll();
        } catch (error) {
          ElMessage.error(error.message);
        }
      }
      function editSource(source) { editingSource.value = { ...source }; editSourceDialogVisible.value = true; }
      async function saveEditedSource() { try { await request("/api/scan-sources/" + editingSource.value.id, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: editingSource.value.name, rootPath: editingSource.value.path, recursive: editingSource.value.recursive, stableWaitSeconds: editingSource.value.stableWaitSeconds, autoScan: editingSource.value.autoScan, transferPolicy: editingSource.value.postAction }) }); ElMessage.success("扫描源已更新"); editSourceDialogVisible.value = false; await loadSources(); } catch (error) { ElMessage.error(error.message); } }
      async function confirmDeleteSource(index) { try { await ElMessageBox.confirm("确定移除此扫描源吗？不会删除磁盘上的媒体文件。", "移除扫描源", { type: "warning" }); await request("/api/scan-sources/" + scanSources.value[index].id, { method: "DELETE" }); ElMessage.success("扫描源已删除"); await loadSources(); } catch (_) {} }
      async function retryTask(task) { try { const result = await request("/api/tasks/" + task.id + "/retry", { method: "POST" }); ElMessage.success("已创建重试任务"); await loadTasks(); const next = tasks.value.find((item) => item.id === result.id); if (next) openTaskDetail(next); } catch (error) { ElMessage.error(error.message); } }
      async function confirmCancelTask(task) { try { await ElMessageBox.confirm("确认取消该任务吗？", "取消任务", { type: "warning" }); await request("/api/tasks/" + task.id + "/cancel", { method: "POST" }); ElMessage.info("已发出取消请求"); await loadTasks(); } catch (_) {} }
      async function deleteTask(task) { try { await ElMessageBox.confirm("确定删除该任务记录吗？", "删除记录", { type: "warning" }); await request("/api/tasks/" + task.id, { method: "DELETE" }); ElMessage.success("任务记录已删除"); currentTab.value = "tasks"; await loadTasks(); } catch (_) {} }
      function exportFile(type) { if (currentTask.value) window.open("/api/tasks/" + currentTask.value.id + "/download?type=" + type, "_blank"); }
      function handlePlaySegment(segment) { ElMessage.info("已定位到 " + segment.start + " 秒"); }
      function getAiActionLabel(value) { return ({ oneSentence: "一句话总结", detailedSummary: "详细总结", keyPoints: "核心观点提炼", outline: "内容框架大纲", quotes: "金句提取", rewrite: "短视频文案改写" }[value] || value); }
      async function runAiAnalysis() { if (!currentTask.value) return; isAiAnalyzing.value = true; aiProgress.value = 30; try { await request("/api/tasks/" + currentTask.value.id + "/analyses", { method: "POST" }); await new Promise((resolve) => setTimeout(resolve, 500)); currentTask.value.aiResult = { type: selectedAiAction.value, content: "AI Provider 尚未启用；已保留分析请求，可在系统设置中配置接口。" }; aiProgress.value = 100; } catch (error) { ElMessage.error(error.message); } finally { isAiAnalyzing.value = false; } }
      async function checkMediaTools() { isCheckingMediaTools.value = true; try { const result = await request("/api/system/check-media-tools", { method: "POST" }); result.available ? ElMessage.success("FFmpeg / FFprobe 可用") : ElMessage.error(result.message); } catch (error) { ElMessage.error(error.message); } finally { isCheckingMediaTools.value = false; } }
      function testAiConnection() { isTestingAi.value = true; setTimeout(() => { isTestingAi.value = false; ElMessage.info("AI Provider 测试接口将在后续版本启用"); }, 500); }
      function saveSystemSettings() { localStorage.setItem("transcriber_settings", JSON.stringify(settings.value)); localStorage.setItem("transcriber_ai_config", JSON.stringify(aiConfig.value)); ElMessage.success("配置已保存"); }
      function refreshTaskList() { loadTasks().then(() => ElMessage.success("任务队列已刷新")); }

      function connectSocket() {
        if (!window.WebSocket) return;
        const socket = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws/tasks");
        socket.onopen = () => ElMessage.success("实时任务通道已连接");
        socket.onmessage = (event) => { let payload; try { payload = JSON.parse(event.data); } catch (_) { return; } if (["task.updated", "task.completed", "task.failed"].includes(payload.type)) { loadTasks(); if (currentTaskId.value && Number(currentTaskId.value) === Number(payload.taskId)) { const task = tasks.value.find((item) => item.id === Number(payload.taskId)); if (task) loadTaskDetail(task); } } };
        socket.onclose = () => setTimeout(connectSocket, 2500);
      }

      onMounted(async () => {
        applyTheme();
        const saved = JSON.parse(localStorage.getItem("transcriber_settings") || "null");
        if (saved) settings.value = { ...settings.value, ...saved };
        const savedAi = JSON.parse(localStorage.getItem("transcriber_ai_config") || "null");
        if (savedAi) aiConfig.value = { ...aiConfig.value, ...savedAi };
        try {
          const info = await request("/api/system/info");
          settings.value = { ...settings.value, asrDevice: info.asrDevice || settings.value.asrDevice, ffmpegPath: info.ffmpeg || settings.value.ffmpegPath, ffprobePath: info.ffprobe || settings.value.ffprobePath, modelDirPath: info.modelDir || settings.value.modelDirPath };
        } catch (_) { /* 系统信息不可用时保留本地配置 */ }
        await refreshAll();
        connectSocket();
      });
      return { currentTab, currentTaskId, currentTask, isDarkTheme, breadcrumbTitle, toggleTheme, switchTab, scanSources, tasks, taskStats, filteredTasks, taskSearchKeyword, taskFilterStatus, openTaskDetail, refreshTaskList, retryTask, confirmCancelTask, deleteTask, getStatusClass, getStatusLabel, environment, envData, envOverallReady, envLastCheckTime, isEnvChecking, checkLocalEnvironment: loadEnvironment, sourceForm, isScanningSource, handleSaveAndScan, triggerScan, fileSelectionDialogVisible, scannedFiles, selectedFileIds, handleFileSelectionChange, createTasksFromSelection, editSourceDialogVisible, editingSource, editSource, saveEditedSource, confirmDeleteSource, activeTextTab, exportFile, handlePlaySegment, selectedAiAction, isAiAnalyzing, aiProgress, aiConfig, runAiAnalysis, getAiActionLabel, settings, isCheckingMediaTools, checkMediaTools, isTestingAi, testAiConnection, saveSystemSettings };
    },
  });
  Object.entries(ElementPlusIconsVue).forEach(([name, component]) => app.component("i-ep-" + name.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase(), component));
  app.use(ElementPlus).mount("#app");
})();
