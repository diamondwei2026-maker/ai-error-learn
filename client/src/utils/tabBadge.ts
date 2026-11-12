import Taro from '@tarojs/taro'

import { REVIEW_REMINDER_ENABLED } from '@/constants'

import { isWeapp } from './platform'

/** 刷题 tab 在 tabBar 中的下标（首页 0 / 题库 1 / 刷题 2 / 我的 3） */
const QUIZ_TAB_INDEX = 2

/**
 * 同步刷题 tab 角标。
 * 仅微信端支持原生 tabBar 角标，H5 预览静默跳过；失败不影响业务。
 */
export function syncQuizBadge(count: number): void {
  if (!isWeapp) return
  // 学习提醒关闭时目标数量恒为 0，用于清除历史残留角标
  const next = REVIEW_REMINDER_ENABLED ? count : 0
  try {
    if (next > 0) {
      Taro.setTabBarBadge({
        index: QUIZ_TAB_INDEX,
        text: next > 99 ? '99+' : String(next),
      }).catch(() => undefined)
      return
    }
    Taro.removeTabBarBadge({ index: QUIZ_TAB_INDEX }).catch(() => undefined)
  } catch (error) {
    console.warn('[tabBadge] sync failed', error)
  }
}
