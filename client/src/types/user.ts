/** 用户与云端同步相关类型。 */

/** 用户资料（与服务端 /user/me 返回一致） */
export interface UserProfile {
  id: number
  openid: string
  nickname: string | null
  avatarUrl: string | null
}

/** 登录态（持久化于 Storage: u:auth） */
export interface AuthSession {
  accessToken: string
  refreshToken: string
  /** access token 过期时间戳（ms） */
  accessExpireAt: number
  user: UserProfile
}

/** 同步项：错题在云端的表示（仅文本） */
export interface SyncItem {
  id: string
  content: string
  answer: string
  createdAt: number
  updatedAt: number
  /** 逻辑删除标记（墓碑） */
  deleted: boolean
}

/** 本地删除墓碑 */
export interface Tombstone {
  id: string
  updatedAt: number
}
