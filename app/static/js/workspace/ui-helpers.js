/* UI/UX 优化工具函数 */
(function(window) {
  'use strict';

  const { ElMessage, ElMessageBox, ElLoading } = window.ElementPlus || {};

  // 错误消息映射（用户友好提示）
  const errorMessages = {
    'MEDIA_NOT_FOUND': '找不到媒体文件，可能已被移动或删除',
    'FFMPEG_NOT_FOUND': 'FFmpeg 未安装，请先安装 FFmpeg 工具',
    'FFMPEG_ERROR': 'FFmpeg 处理失败，请检查文件是否损坏',
    'ASR_DEPENDENCY_MISSING': '语音识别模块未安装，请运行 pip install -r requirements.txt',
    'ASR_MODEL_NOT_FOUND': '语音识别模型未下载，首次运行时会自动下载',
    'ASR_INFERENCE_ERROR': '语音识别失败，请稍后重试',
    'DATABASE_ERROR': '数据库操作失败，请重试',
    'RECORD_NOT_FOUND': '记录不存在，可能已被删除',
    'TASK_CANCELLED': '任务已取消',
    'TASK_TIMEOUT': '任务执行超时，请检查文件大小和系统性能',
    'SCAN_SOURCE_ERROR': '扫描目录失败，请检查路径和权限',
    'INVALID_PATH': '路径无效，请检查路径是否正确',
    'CONFIGURATION_ERROR': '配置错误，请检查配置文件',
    'INTERNAL_SERVER_ERROR': '服务器内部错误，请稍后重试'
  };

  // 智能错误提示
  function showError(error, defaultMessage = '操作失败') {
    if (!ElMessage) {
      console.error(error);
      return;
    }

    let message = defaultMessage;
    let duration = 5000;

    // 解析错误对象
    if (typeof error === 'string') {
      message = error;
    } else if (error && error.message) {
      message = error.message;
    }

    // 如果是 API 错误响应
    if (error && error.response) {
      try {
        const data = error.response.data;
        if (data && data.error) {
          const errorCode = data.error.code;
          const errorDetail = data.error.detail;

          // 使用友好的错误消息
          message = errorMessages[errorCode] || data.error.message || message;

          // 如果有详细信息，延长显示时间
          if (errorDetail && errorCode === 'FFMPEG_ERROR') {
            duration = 10000;
          }
        }
      } catch (e) {
        // 解析失败，使用默认消息
      }
    }

    ElMessage({
      message: message,
      type: 'error',
      duration: duration,
      showClose: true,
      dangerouslyUseHTMLString: false
    });
  }

  // 成功提示（带图标）
  function showSuccess(message, duration = 3000) {
    if (!ElMessage) return;

    ElMessage({
      message: message,
      type: 'success',
      duration: duration,
      showClose: true
    });
  }

  // 警告提示
  function showWarning(message, duration = 4000) {
    if (!ElMessage) return;

    ElMessage({
      message: message,
      type: 'warning',
      duration: duration,
      showClose: true
    });
  }

  // 信息提示
  function showInfo(message, duration = 3000) {
    if (!ElMessage) return;

    ElMessage({
      message: message,
      type: 'info',
      duration: duration,
      showClose: true
    });
  }

  // 确认对话框（增强版）
  async function confirmAction(options) {
    if (!ElMessageBox) return false;

    const {
      title = '确认操作',
      message = '确定要执行此操作吗？',
      confirmText = '确定',
      cancelText = '取消',
      type = 'warning',
      danger = false,
      showInput = false,
      inputPlaceholder = ''
    } = options;

    try {
      const result = await ElMessageBox.confirm(message, title, {
        confirmButtonText: confirmText,
        cancelButtonText: cancelText,
        type: type,
        distinguishCancelAndClose: true,
        showInput: showInput,
        inputPlaceholder: inputPlaceholder,
        beforeClose: (action, instance, done) => {
          if (action === 'confirm') {
            done();
          } else {
            done();
          }
        }
      });
      return result;
    } catch (error) {
      // 用户取消
      return false;
    }
  }

  // 批量操作确认
  async function confirmBatchAction(count, actionName, itemName = '项') {
    return await confirmAction({
      title: `批量${actionName}确认`,
      message: `确定要${actionName} ${count} ${itemName}吗？此操作不可撤销。`,
      confirmText: `${actionName} ${count} ${itemName}`,
      type: 'warning'
    });
  }

  // 危险操作确认（需要输入确认文本）
  async function confirmDangerousAction(actionName, confirmText = '确认删除') {
    if (!ElMessageBox) return false;

    try {
      await ElMessageBox.confirm(
        `此操作非常危险，请输入 "${confirmText}" 来确认`,
        `${actionName}确认`,
        {
          confirmButtonText: '执行',
          cancelButtonText: '取消',
          type: 'error',
          showInput: true,
          inputPlaceholder: `请输入: ${confirmText}`,
          inputValidator: (value) => {
            if (value === confirmText) {
              return true;
            }
            return `请输入正确的确认文本: ${confirmText}`;
          }
        }
      );
      return true;
    } catch (error) {
      return false;
    }
  }

  // 加载遮罩（全屏）
  function showLoading(message = '加载中...') {
    if (!ElLoading) return null;

    return ElLoading.service({
      lock: true,
      text: message,
      background: 'rgba(0, 0, 0, 0.7)'
    });
  }

  // 进度提示
  async function withProgress(promise, message = '处理中...') {
    const loading = showLoading(message);
    try {
      const result = await promise;
      if (loading) loading.close();
      return result;
    } catch (error) {
      if (loading) loading.close();
      throw error;
    }
  }

  // 操作节流（防止重复点击）
  function throttle(func, wait = 1000) {
    let timer = null;
    let lastTime = 0;

    return function(...args) {
      const now = Date.now();

      if (now - lastTime >= wait) {
        lastTime = now;
        return func.apply(this, args);
      } else {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => {
          lastTime = Date.now();
          func.apply(this, args);
        }, wait - (now - lastTime));
      }
    };
  }

  // 防抖（用于搜索输入）
  function debounce(func, wait = 300) {
    let timer = null;

    return function(...args) {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        func.apply(this, args);
      }, wait);
    };
  }

  // 导出工具函数
  window.UIHelpers = {
    showError,
    showSuccess,
    showWarning,
    showInfo,
    confirmAction,
    confirmBatchAction,
    confirmDangerousAction,
    showLoading,
    withProgress,
    throttle,
    debounce
  };

})(window);
