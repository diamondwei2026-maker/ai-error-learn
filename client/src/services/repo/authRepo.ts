import Taro from '@tarojs/taro'

import { STORAGE_KEYS } from '@/constants'
import type { AuthSession, Tombstone } from '@/types/user'

/**
 * 登录态与同步元数据的本地持久化。
 * 页面与业务服务一律通过本模块访问存储，禁止直接调用 Taro.setStorage。
 */
export const authRepo = {
  getSession(): AuthSession | null {
    try {
      const raw = Taro.getStorageSync(STORAGE_KEYS.auth)
      if (raw && typeof raw === 'object' && (raw as AuthSession).accessToken) {
        return raw as AuthSession
      }
    } catch (error) {
      console.error('[authRepo] getSession failed', error)
    }
    return null
  },

  saveSession(session: AuthSession | null): void {
    try {
      if (session) {
        Taro.setStorageSync(STORAGE_KEYS.auth, session)
      } else {
        Taro.removeStorageSync(STORAGE_KEYS.auth)
      }
    } catch (error) {
      console.error('[authRepo] saveSession failed', error)
    }
  },

  clearSession(): void {
    this.saveSession(null)
  },

  listTombstones(): Tombstone[] {
    try {
      const raw = Taro.getStorageSync(STORAGE_KEYS.removed)
      return Array.isArray(raw) ? (raw as Tombstone[]) : []
    } catch (error) {
      console.error('[authRepo] listTombstones failed', error)
      return []
    }
  },

  saveTombstones(list: Tombstone[]): void {
    try {
      Taro.setStorageSync(STORAGE_KEYS.removed, list)
    } catch (error) {
      console.error('[authRepo] saveTombstones failed', error)
    }
  },

  /** 记录一条删除墓碑（同 id 覆盖，保留最新时间） */
  addTombstone(id: string): void {
    const list = this.listTombstones().filter((item) => item.id !== id)
    list.push({ id, updatedAt: Date.now() })
    this.saveTombstones(list)
  },

  removeTombstone(id: string): void {
    const list = this.listTombstones()
    const next = list.filter((item) => item.id !== id)
    if (next.length !== list.length) this.saveTombstones(next)
  },

  getSyncCursor(): number {
    try {
      const raw = Taro.getStorageSync(STORAGE_KEYS.syncCursor)
      return typeof raw === 'number' && Number.isFinite(raw) ? raw : 0
    } catch (error) {
      console.error('[authRepo] getSyncCursor failed', error)
      return 0
    }
  },

  setSyncCursor(cursor: number): void {
    try {
      Taro.setStorageSync(STORAGE_KEYS.syncCursor, cursor)
    } catch (error) {
      console.error('[authRepo] setSyncCursor failed', error)
    }
  },

  /** 是否已引导过「首次登录完善资料」 */
  isNicknamePrompted(): boolean {
    try {
      return Taro.getStorageSync(STORAGE_KEYS.nickPrompted) === true
    } catch (error) {
      console.error('[authRepo] isNicknamePrompted failed', error)
      return false
    }
  },

  /** 标记已引导过「首次登录完善资料」（仅首次引导一次） */
  markNicknamePrompted(): void {
    try {
      Taro.setStorageSync(STORAGE_KEYS.nickPrompted, true)
    } catch (error) {
      console.error('[authRepo] markNicknamePrompted failed', error)
    }
  },

  /** 注销账号时清空全部登录/同步元数据 */
  clearAll(): void {
    try {
      Taro.removeStorageSync(STORAGE_KEYS.auth)
      Taro.removeStorageSync(STORAGE_KEYS.removed)
      Taro.removeStorageSync(STORAGE_KEYS.syncCursor)
      Taro.removeStorageSync(STORAGE_KEYS.nickPrompted)
    } catch (error) {
      console.error('[authRepo] clearAll failed', error)
    }
  },
}
