import dayjs from 'dayjs'

import { isWeapp } from './platform'

/** 首页/题库通用的时间展示：今天 HH:mm / 昨天 HH:mm / M月D日 / YYYY年M月D日 */
export function formatTime(ts: number): string {
  const now = dayjs()
  const target = dayjs(ts)
  if (target.isSame(now, 'day')) return `今天 ${target.format('HH:mm')}`
  if (target.isSame(now.subtract(1, 'day'), 'day')) return `昨天 ${target.format('HH:mm')}`
  if (target.isSame(now, 'year')) return target.format('M月D日')
  return target.format('YYYY年M月D日')
}

/** 秒 → m:ss（本轮用时） */
export function formatDuration(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(safe / 60)
  const rest = safe % 60
  return `${minutes}:${String(rest).padStart(2, '0')}`
}

/** 字节 → 人类可读（KB / MB） */
export function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return isWeapp ? '—' : '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
