import Taro from '@tarojs/taro'

import { usePrivacyStore } from '@/store/privacyStore'
import { isWeapp } from '@/utils/platform'

/**
 * 隐私授权编排（仅微信小程序生效，H5 / 其他端直接 noop）。
 *
 * 策略：**启动非阻断 + 被动兜底 + 主动前置**
 * - 启动：查询微信侧授权状态，需要授权则弹出弹层；用户可「暂不授权」，主流程照常可用；
 * - 被动：任意隐私接口被调用且未同步过同意状态时，弹同一弹层，并在用户选择后 resolve；
 * - 主动：`<input type="nickname">` 聚焦不会触发被动监听，需在调用前主动 `requireAuthorize`。
 */
export const privacyService = {
  /** 注册被动监听（app 启动调用一次）。失败不抛出，避免阻塞启动。 */
  init(): void {
    if (!isWeapp) return
    try {
      Taro.onNeedPrivacyAuthorization((resolve) => {
        console.info('[privacyService] onNeedPrivacyAuthorization triggered')
        usePrivacyStore.getState().open(resolve)
      })
    } catch (error) {
      console.error('[privacyService] init failed', error)
    }
  },

  /** 启动时主动查询授权状态：需要授权则弹出弹层（非阻断）。失败不抛出。 */
  checkOnLaunch(): void {
    if (!isWeapp) return
    try {
      Taro.getPrivacySetting({
        success: (res) => {
          console.info('[privacyService] needAuthorization =', res.needAuthorization)
          if (res.needAuthorization) {
            usePrivacyStore.getState().open(null, res.privacyContractName)
          }
        },
        fail: (error) => {
          console.error('[privacyService] getPrivacySetting failed', error)
        },
      })
    } catch (error) {
      console.error('[privacyService] checkOnLaunch failed', error)
    }
  },

  /** 打开微信平台《用户隐私保护指引》 */
  openContract(): void {
    if (!isWeapp) return
    try {
      Taro.openPrivacyContract({
        fail: (error) => {
          console.error('[privacyService] openPrivacyContract failed', error)
        },
      })
    } catch (error) {
      console.error('[privacyService] openPrivacyContract failed', error)
    }
  },

  /**
   * 主动触发一次隐私授权校验（用于昵称输入聚焦、拍照/相册等前置守卫）。
   * @returns 是否已获授权：已同意返回 true；用户拒绝或调用异常返回 false
   */
  requireAuthorize(): Promise<boolean> {
    if (!isWeapp) return Promise.resolve(true)
    return new Promise<boolean>((resolve) => {
      try {
        Taro.requirePrivacyAuthorize({
          success: () => resolve(true),
          fail: (error) => {
            console.info('[privacyService] privacy not authorized', error)
            resolve(false)
          },
        })
      } catch (error) {
        console.error('[privacyService] requirePrivacyAuthorize failed', error)
        resolve(false)
      }
    })
  },
}
