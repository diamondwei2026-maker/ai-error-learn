/** 生成唯一 ID：时间戳（36 进制） + 随机串 */
export function createId(): string {
  const ts = Date.now().toString(36)
  const rand = Math.random().toString(36).slice(2, 8)
  return `${ts}${rand}`
}
