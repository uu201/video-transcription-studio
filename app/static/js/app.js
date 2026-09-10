// 页面层只处理交互和反馈，任务状态仍以服务端 API 为准。
const toast = (message, isError = false) => {
  const element = document.getElementById('toast');
  if (!element) return;
  element.textContent = message;
  element.classList.toggle('toast-error', isError);
  element.classList.add('show');
  window.clearTimeout(window.__toastTimer);
  window.__toastTimer = window.setTimeout(() => element.classList.remove('show'), 3200);
};

function connectTaskSocket() {
  // 所有页面共用一条 WebSocket，任务阶段变化不再依赖定时刷新。
  if (!window.WebSocket) return;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(protocol + '//' + window.location.host + '/ws/tasks');
  window.__taskSocket = socket;
  const connection = document.querySelector('.connection');
  socket.addEventListener('open', () => { if (connection) connection.innerHTML = '<span class="status-dot"></span>REALTIME CONNECTED'; });
  socket.addEventListener('message', (event) => {
    let payload;
    try { payload = JSON.parse(event.data); } catch (error) { return; }
    if (!payload.type || payload.type === 'connected' || payload.type === 'ping' || payload.type === 'task.snapshot') return;
    const label = payload.type === 'task.completed' ? '任务已完成' : payload.type === 'task.failed' ? '任务处理失败' : payload.message || '任务状态已更新';
    toast('任务 #' + String(payload.taskId).padStart(4, '0') + ' · ' + label, payload.type === 'task.failed');
    // 服务端状态是唯一来源，短暂等待数据库事务提交后刷新当前列表或详情。
    window.clearTimeout(window.__taskRefreshTimer);
    window.__taskRefreshTimer = window.setTimeout(() => {
      if (document.visibilityState === 'visible' && (window.location.pathname === '/tasks' || window.location.pathname === '/' || window.location.pathname.indexOf('/tasks/') === 0)) window.location.reload();
    }, 450);
  });
  socket.addEventListener('close', () => {
    if (connection) connection.innerHTML = '<span class="status-dot status-dot-warn"></span>RECONNECTING';
    window.clearTimeout(window.__taskSocketTimer);
    window.__taskSocketTimer = window.setTimeout(connectTaskSocket, 2500);
  });
}

connectTaskSocket();

async function requestEnvironment() {
  const response = await fetch('/api/system/environment', {cache: 'no-store'});
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || '环境检测失败');
  return result;
}

function renderEnvironmentFallback(result) {
  // Vue CDN 不可用时，仍让环境检测卡片保持可用。
  const loading = document.getElementById('environment-loading');
  const content = document.getElementById('environment-content');
  if (!loading || !content) return;
  loading.style.display = 'none';
  content.style.display = 'block';
  const summary = content.querySelector('.environment-summary');
  const items = content.querySelector('.environment-grid');
  summary.innerHTML = '<span class="environment-state ' + (result.overall === 'ok' ? 'state-ok' : 'state-attention') + '"><i></i>' + (result.overall === 'ok' ? '环境就绪' : '需要处理') + '</span><small>' + result.checkedAt + '</small>';
  items.innerHTML = result.items.map((item) => '<article class="environment-item"><div class="environment-item-top"><span>' + item.label + '</span><i class="env-icon env-' + item.status + '">' + (item.status === 'ok' ? '✓' : item.status === 'warn' ? '!' : '×') + '</i></div><strong>' + item.value + '</strong><small>' + item.detail + '</small></article>').join('');
}

// Vue 只承载全局工作台状态，页面内容仍由后端模板提供，启动不依赖构建工具。
if (window.Vue) {
  const root = document.getElementById('console-app');
  if (root) {
    window.__consoleApp = Vue.createApp({
      data() {
        return {
          darkMode: localStorage.getItem('content-lab-theme') !== 'light',
          environment: {loading: true, overall: 'attention', checkedAt: '', items: []},
        };
      },
      methods: {
        toggleTheme() {
          this.darkMode = !this.darkMode;
          localStorage.setItem('content-lab-theme', this.darkMode ? 'dark' : 'light');
          document.documentElement.classList.toggle('light-mode', !this.darkMode);
        },
        async refreshEnvironment() {
          this.environment.loading = true;
          try {
            this.environment = await requestEnvironment();
          } catch (error) {
            this.environment = {loading: false, overall: 'attention', checkedAt: '', items: [{key: 'request', label: '环境接口', status: 'error', value: '检测失败', detail: error.message || '请确认服务正在运行'}]};
            toast(error.message || '环境检测失败', true);
          }
        },
      },
      mounted() {
        document.documentElement.classList.toggle('light-mode', !this.darkMode);
        if (root.dataset.page === 'dashboard') this.refreshEnvironment();
      },
    }).mount(root);
  }
} else if (document.getElementById('environment-panel')) {
  requestEnvironment().then(renderEnvironmentFallback).catch((error) => toast(error.message || '环境检测失败', true));
}

const form = document.getElementById('source-form');
if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submit = form.querySelector('button[type="submit"]');
    const data = new FormData(form);
    const payload = {
      name: data.get('name'),
      rootPath: data.get('rootPath'),
      recursive: data.has('recursive'),
      stableWaitSeconds: Number(data.get('stableWaitSeconds') || 0),
      transferPolicy: data.get('transferPolicy'),
    };
    submit.disabled = true;
    try {
      const createdResponse = await fetch('/api/scan-sources', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
      });
      const created = await createdResponse.json();
      if (!createdResponse.ok) throw new Error(created.detail || '保存扫描源失败');
      const scanResponse = await fetch('/api/scan-sources/' + created.id + '/scan', {method: 'POST'});
      const result = await scanResponse.json();
      if (!scanResponse.ok) throw new Error(result.detail || '扫描失败');
      toast('扫描完成：发现 ' + result.discovered + ' 个文件，新增 ' + result.created + ' 个任务');
      window.setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      toast(error.message || '请求失败', true);
      submit.disabled = false;
    }
  });
}

document.querySelectorAll('.scan-button').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  event.stopPropagation();
  button.disabled = true;
  try {
    const response = await fetch('/api/scan-sources/' + button.dataset.id + '/scan', {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '扫描失败');
    toast('扫描完成：新增 ' + result.created + ' 个任务');
    window.setTimeout(() => window.location.reload(), 700);
  } catch (error) {
    toast(error.message || '扫描失败', true);
    button.disabled = false;
  }
}));

document.querySelectorAll('.edit-source').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  event.stopPropagation();
  const name = window.prompt('扫描源名称', button.dataset.name);
  if (name === null || !name.trim()) return;
  const rootPath = window.prompt('输入目录绝对路径', button.dataset.path);
  if (rootPath === null || !rootPath.trim()) return;
  try {
    const response = await fetch('/api/scan-sources/' + button.dataset.id, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name: name.trim(), rootPath: rootPath.trim(), recursive: true, stableWaitSeconds: 3, transferPolicy: 'keep'})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '更新扫描源失败');
    toast('扫描源已更新');
    window.setTimeout(() => window.location.reload(), 600);
  } catch (error) { toast(error.message || '更新失败', true); }
}));

document.querySelectorAll('.delete-source').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  event.stopPropagation();
  if (!window.confirm('删除扫描源会同时删除其媒体索引和任务记录，确认继续吗？')) return;
  try {
    const response = await fetch('/api/scan-sources/' + button.dataset.id, {method: 'DELETE'});
    if (!response.ok) { const result = await response.json(); throw new Error(result.detail || '删除失败'); }
    toast('扫描源已删除');
    window.setTimeout(() => window.location.reload(), 600);
  } catch (error) { toast(error.message || '删除失败', true); }
}));

function filterTasks() {
  const status = document.getElementById('task-status-filter');
  const search = document.getElementById('task-search');
  const empty = document.getElementById('task-filter-empty');
  if (!status || !search) return;
  const keyword = search.value.trim().toLowerCase();
  let visible = 0;
  document.querySelectorAll('.queue-row[data-task-id]').forEach((row) => {
    const matchesStatus = status.value === 'all' || row.dataset.status === status.value;
    const matchesSearch = !keyword || (row.dataset.search || '').toLowerCase().includes(keyword);
    row.classList.toggle('is-hidden', !(matchesStatus && matchesSearch));
    if (matchesStatus && matchesSearch) visible += 1;
  });
  if (empty) empty.hidden = visible !== 0;
}

document.getElementById('task-status-filter')?.addEventListener('change', filterTasks);
document.getElementById('task-search')?.addEventListener('input', filterTasks);

document.querySelectorAll('.cancel-task').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  event.stopPropagation();
  if (!window.confirm('确认请求取消这个任务吗？Worker 会在当前阶段结束后停止。')) return;
  button.disabled = true;
  try {
    const response = await fetch('/api/tasks/' + button.dataset.id + '/cancel', {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '取消失败');
    toast('已发出取消请求');
  } catch (error) { toast(error.message || '取消失败', true); button.disabled = false; }
}));

document.querySelectorAll('.retry-task').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  event.stopPropagation();
  await retryTask(Number(button.dataset.id));
}));

async function checkTools() {
  const output = document.getElementById('tool-result');
  if (!output) return;
  output.textContent = '检查中…';
  try {
    const result = await fetch('/api/system/check-media-tools', {method: 'POST'}).then((response) => response.json());
    output.textContent = result.available ? '✓ FFmpeg / FFprobe 可用' : '× ' + result.message;
  } catch (error) {
    output.textContent = '× 无法连接到系统检查接口';
  }
}

async function retryTask(taskId) {
  try {
    const response = await fetch('/api/tasks/' + taskId + '/retry', {method: 'POST'});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || '重试失败');
    toast('已创建新的重试任务');
    window.setTimeout(() => { window.location.href = '/tasks/' + result.id; }, 700);
  } catch (error) {
    toast(error.message || '重试失败', true);
  }
}

function seekTo(seconds) {
  // 详情页嵌入视频后复用此方法；没有播放器时不影响文本阅读。
  const video = document.querySelector('video');
  if (video) {
    video.currentTime = seconds;
    video.play();
  }
}

// 外部 Vue CDN 不可用时，主题切换仍保持可用。
if (!window.Vue) {
  const themeButton = document.querySelector('.theme-button');
  if (themeButton) {
    themeButton.addEventListener('click', () => {
      const light = !document.documentElement.classList.contains('light-mode');
      document.documentElement.classList.toggle('light-mode', light);
      localStorage.setItem('content-lab-theme', light ? 'light' : 'dark');
    });
  }
}
