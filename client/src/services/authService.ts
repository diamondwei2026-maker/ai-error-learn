import Taro from '@tarojs/taro'

import type { AuthSession } from '@/types/user'

import { request, type SessionData } from './request'
import { authRepo } from './repo/authRepo'

/**
 * 登录态编排：wx.login 取 code → 换取后端 JWT → 本地持久化。
 * 退出登录仅清除本地登录态，本地错题数据保留。
 */
export const authService = {
  /** 启动时恢复登录态（不发请求） */
  restore(): AuthSession | null {
    return authRepo.getSession()
  },

  /** 微信一键登录 */
  async login(): Promise<AuthSession> {
    const loginResult = await Taro.login()
    const code = loginResult?.code
    if (!code) {
      throw new Error('微信登录失败，请重试')
    }
    const data = await request<SessionData>('/api/v1/auth/login', {
      method: 'POST',
      data: { code },
      auth: false,
    })
    const session: AuthSession = {
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      accessExpireAt: data.accessExpireAt,
      user: data.user,
    }
    authRepo.saveSession(session)
    console.info('[authService] login success, userId =', data.user.id)
    return session
  },

  /** 退出登录（清登录态，保数据） */
  logout(): void {
    authRepo.clearSession()
    console.info('[authService] logout')
  },
}
