/**
 * 将后端返回的 ISO 8601 时间转换为用户本地时间。
 * 统一使用 24 小时制，避免直接展示 T、时区偏移和尾部空格。
 */
export function formatDateTime(value, options = {}) {
  if (value === null || value === undefined || String(value).trim() === '') return '--'

  const raw = String(value).trim()
  const date = value instanceof Date ? value : new Date(raw)
  if (Number.isNaN(date.getTime())) {
    return raw.replace('T', ' ').replace(/\s+/g, ' ').trim()
  }

  const parts = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: options.withSeconds === false ? undefined : '2-digit',
    hour12: false,
    hourCycle: 'h23'
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]))
  const time = [values.hour, values.minute, options.withSeconds === false ? null : values.second]
    .filter(Boolean)
    .join(':')
  return `${values.year}-${values.month}-${values.day} ${time}`
}

/** Format elapsed wall-clock time for a queued task. */
export function formatElapsed(startAt, finishedAt, now = Date.now()) {
  if (!startAt) return '--'

  const start = new Date(startAt).getTime()
  if (Number.isNaN(start)) return '--'
  const end = finishedAt ? new Date(finishedAt).getTime() : now
  if (Number.isNaN(end) || end < start) return '--'

  const totalSeconds = Math.floor((end - start) / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map(value => String(value).padStart(2, '0')).join(':')
}
