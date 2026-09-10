/* WebSocket 连接管理 */
(function(window) {
  'use strict';

  const { ElMessage } = window.ElementPlus || {};

  class TaskSocket {
    constructor(onMessage) {
      this.socket = null;
      this.onMessage = onMessage;
      this.reconnectAttempts = 0;
      this.maxReconnectDelay = 30000;
      this.heartbeatInterval = null;
      this.messageBuffer = [];
      this.processTimer = null;
    }

    connect() {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        return;
      }

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${window.location.host}/ws/tasks`;

      try {
        this.socket = new WebSocket(url);
        this.setupHandlers();
      } catch (error) {
        console.error('WebSocket 连接失败:', error);
        this.scheduleReconnect();
      }
    }

    setupHandlers() {
      this.socket.onopen = () => {
        console.log('WebSocket 已连接');
        if (ElMessage) {
          ElMessage.success('实时任务通道已连接');
        }
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.socket.onmessage = (event) => {
        this.handleMessage(event);
      };

      this.socket.onclose = () => {
        console.log('WebSocket 连接关闭');
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket 错误:', error);
      };
    }

    handleMessage(event) {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (error) {
        return;
      }

      // 忽略连接和心跳消息
      if (!payload.type || payload.type === 'connected' || payload.type === 'ping') {
        return;
      }

      // 消息缓冲和节流
      this.messageBuffer.push(payload);
      if (this.messageBuffer.length > 10) {
        this.messageBuffer = this.messageBuffer.slice(-5);
      }

      this.scheduleProcess();
    }

    scheduleProcess() {
      if (this.processTimer) return;

      this.processTimer = setTimeout(() => {
        this.processMessages();
        this.processTimer = null;
      }, 100); // 100ms 节流
    }

    processMessages() {
      const messages = [...this.messageBuffer];
      this.messageBuffer = [];

      messages.forEach(payload => {
        if (this.onMessage) {
          this.onMessage(payload);
        }
      });
    }

    startHeartbeat() {
      this.stopHeartbeat();
      this.heartbeatInterval = setInterval(() => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          try {
            this.socket.send(JSON.stringify({ type: 'ping' }));
          } catch (error) {
            console.error('心跳发送失败:', error);
          }
        }
      }, 30000); // 30秒心跳
    }

    stopHeartbeat() {
      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
        this.heartbeatInterval = null;
      }
    }

    scheduleReconnect() {
      // 指数退避重连
      const delay = Math.min(
        1000 * Math.pow(2, this.reconnectAttempts),
        this.maxReconnectDelay
      );

      console.log(`将在 ${delay}ms 后重新连接...`);
      this.reconnectAttempts++;

      setTimeout(() => {
        this.connect();
      }, delay);
    }

    disconnect() {
      this.stopHeartbeat();
      if (this.socket) {
        this.socket.close();
        this.socket = null;
      }
    }
  }

  // 导出到全局
  window.TaskSocket = TaskSocket;

})(window);
