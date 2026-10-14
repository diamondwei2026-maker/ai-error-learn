import Taro from '@tarojs/taro'

import { API_BASE, AUTH_ERROR_MESSAGES } from '@/constants'
import type { UserProfile } from '@/types/user'

import { ApiRequestError, request } from './request'
import { authRepo } from './repo/authRepo'

interface Envelope {
  code: number
  message?: string
  data?: { user: UserProfile }
}

function persistUser(user: UserProfile): UserProfile {
  const session = authRepo.getSession()
  if (session) authRepo.saveSession({ ...session, user })
  return user
}

/** 用户资料：查询、改昵称、换头像、注销。 */
export const userService = {
  async me(): Promise<UserProfile> {
    const data = await request<{ user: UserProfile }>('/api/v1/user/me')
    return persistUser(data.user)
  },

  async updateNickname(nickname: string): Promise<UserProfile> {
    const data = await request<{ user: UserProfile }>('/api/v1/user/me', {
      method: 'PATCH',
      data: { nickname },
    })
    return persistUser(data.user)
  },

  /** 上传头像（chooseAvatar 的临时路径）并更新资料 */
  async updateAvatar(tempFilePath: string): Promise<UserProfile> {
    const session = authRepo.getSession()
    let raw: string
    try {
      const result = await Taro.uploadFile({
        url: `${API_BASE}/api/v1/user/avatar`,
        filePath: tempFilePath,
        name: 'file',
        header: session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {},
        timeout: 30000,
      })
      raw = result.data
    } catch (error) {
      console.error('[userService] uploadAvatar failed', error)
      throw new ApiRequestError(0, '头像上传失败，请重试')
    }

    let body: Envelope = { code: -1 }
    try {
      body = JSON.parse(raw) as Envelope
    } catch (error) {
      console.error('[userService] parse avatar response failed', error)
    }
    if (body.code !== 0 || !body.data) {
      throw new ApiRequestError(body.code, body.message || AUTH_ERROR_MESSAGES[body.code] || '头像上传失败')
    }
    return persistUser(body.data.user)
  },

  /** 注销账号：删除云端用户及其全部错题数据 */
  async deleteAccount(): Promise<void> {
    await request<{ deleted: boolean }>('/api/v1/user/delete', { method: 'POST' })
    console.info('[userService] account deleted')
  },
}
