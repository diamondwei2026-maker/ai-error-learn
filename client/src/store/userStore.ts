import { create } from 'zustand'

import { SCHEMA_VERSION } from '@/constants'
import { authService } from '@/services/authService'
import { authRepo } from '@/services/repo/authRepo'
import { fileRepo } from '@/services/repo/fileRepo'
import { storageRepo } from '@/services/repo/storageRepo'
import { syncService } from '@/services/syncService'
import { userService } from '@/services/userService'
import type { UserProfile } from '@/types/user'

interface UserState {
  /** 当前用户资料（未登录为 null） */
  user: UserProfile | null
  isLoggedIn: boolean
  /** 微信一键登录；成功后自动触发一次云端同步 */
  login: () => Promise<void>
  /** 退出登录：清登录态，本地错题保留 */
  logout: () => void
  /** 从本地存储恢复登录态（启动时调用） */
  restore: () => void
  /** 更新资料（昵称 / 头像临时路径） */
  updateProfile: (patch: { nickname?: string; avatarTempPath?: string }) => Promise<void>
  /** 注销账号：删除云端数据 + 清除本地全部数据 */
  deleteAccount: () => Promise<void>
}

/** 注销时清空本地全部数据（错题、原图、元数据、登录态、同步元数据） */
function clearAllLocalData(): void {
  const list = storageRepo.listQuestions()
  list.forEach((item) => fileRepo.removeImage(item.imagePath))
  storageRepo.saveQuestions([])
  storageRepo.saveMeta({ schemaVersion: SCHEMA_VERSION, questionCount: 0, imageBytes: 0 })
  authRepo.clearAll()
}

export const useUserStore = create<UserState>((set, get) => ({
  user: null,
  isLoggedIn: false,

  login: async () => {
    const session = await authService.login()
    set({ user: session.user, isLoggedIn: true })
    await syncService.syncNow()
  },

  logout: () => {
    authService.logout()
    set({ user: null, isLoggedIn: false })
  },

  restore: () => {
    const session = authService.restore()
    set({ user: session?.user ?? null, isLoggedIn: Boolean(session) })
  },

  updateProfile: async (patch) => {
    let user = get().user
    if (patch.nickname !== undefined) {
      user = await userService.updateNickname(patch.nickname)
    }
    if (patch.avatarTempPath) {
      user = await userService.updateAvatar(patch.avatarTempPath)
    }
    if (user) set({ user, isLoggedIn: true })
  },

  deleteAccount: async () => {
    await userService.deleteAccount()
    clearAllLocalData()
    set({ user: null, isLoggedIn: false })
    console.info('[userStore] account deleted, local data cleared')
  },
}))
