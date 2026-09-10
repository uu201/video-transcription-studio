// 页面交互只负责请求 API，不在浏览器复制业务逻辑。
const toast = (message, isError = false) => { const element = document.getElementById('toast'); if (!element) return; element.textContent = message; element.style.background = isError ? '#ee776d' : ''; element.classList.add('show'); setTimeout(() => element.classList.remove('show'), 2800); };

const form = document.getElementById('source-form');
if (form) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const payload = { name: data.get('name'), rootPath: data.get('rootPath'), recursive: data.has('recursive'), stableWaitSeconds: Number(data.get('stableWaitSeconds') || 0), transferPolicy: data.get('transferPolicy') };
    try {
      const created = await fetch('/api/scan-sources', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
      if (!created.ok) throw new Error((await created.json()).detail || '保存扫描源失败');
      const source = await created.json();
      const scan = await fetch(`/api/scan-sources/${source.id}/scan`, { method: 'POST' });
      const result = await scan.json();
      toast(`已发现 ${result.discovered} 个文件，创建 ${result.created} 个任务`);
      setTimeout(() => window.location.reload(), 900);
    } catch (error) { toast(error.message, true); }
  });
}

document.querySelectorAll('.scan-button').forEach((button) => button.addEventListener('click', async (event) => {
  event.preventDefault();
  try { const response = await fetch(`/api/scan-sources/${button.dataset.id}/scan`, { method: 'POST' }); const result = await response.json(); toast(`扫描完成：新增 ${result.created} 个任务`); } catch (error) { toast('扫描失败', true); }
}));

async function checkTools() {
  const output = document.getElementById('tool-result');
  output.textContent = '检查中…';
  const result = await fetch('/api/system/check-media-tools', { method: 'POST' }).then((response) => response.json());
  output.textContent = result.available ? '✓ FFmpeg / FFprobe 可用' : `× ${result.message}`;
}

function seekTo(seconds) {
  // 详情页未来嵌入视频时复用此方法；当前没有播放器则保留可用的时间定位 API。
  const video = document.querySelector('video');
  if (video) { video.currentTime = seconds; video.play(); }
}
