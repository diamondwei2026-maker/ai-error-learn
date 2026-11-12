import Taro from '@tarojs/taro'

import { STORAGE_KEYS } from '@/constants'
import { isWeapp } from '@/utils/platform'

import { request } from './request'

/** 服务端推送配置（GET /api/v1/reminder/config） */
export interface ReminderConfig {
  enabled: boolean
  templateId: string
  page: string
  quietStart: number
  quietEnd: number
}

/** 开关操作结果：on 为最终开关状态，subscribed 表示是否拿到微信订阅授权 */
export interface ReminderResult {
  on: boolean
  subscribed: boolean
  message: string
}

const DEFAULT_CONFIG: ReminderConfig = {
  enabled: false,
  templateId: '',
  page: 'pages/quiz/index',
  quietStart: 21,
  quietEnd: 8,
}

let cachedConfig: ReminderConfig | null = null
let loadingConfig: Promise<ReminderConfig> | null = null
/** 同一 session 内只主动弹一次订阅面板 */
let prompted = false

function readMirror(): boolean {
  try {
    return Boolean(Taro.getStorageSync(STORAGE_KEYS.reminderOn))
  } catch (error) {
    console.error('[reminderService] readMirror failed', error)
    return false
  }
}

function writeMirror(on: boolean): void {
  try {
    Taro.setStorageSync(STORAGE_KEYS.reminderOn, on)
  } catch (error) {
    console.error('[reminderService] writeMirror failed', error)
  }
}

/**
 * 复习提醒：拉取推送配置、请求一次性订阅授权并上报结果。
 * 模板未配置 / 非微信端 / 授权失败一律降级为站内提醒，不阻塞复习流程。
 */
export const reminderService = {
  /** 本地镜像开关（订阅状态只在授权/关闭时上报，不做服务端拉取） */
  isOn(): boolean {
    return readMirror()
  },

  /** 推送配置：无鉴权；失败或未配置时返回默认值 */
  async getConfig(force = false): Promise<ReminderConfig> {
    if (!force && cachedConfig) return cachedConfig
    if (!loadingConfig) {
      loadingConfig = request<ReminderConfig>('/api/v1/reminder/config', { auth: false })
        .then((config) => {
          cachedConfig = { ...DEFAULT_CONFIG, ...config }
          return cachedConfig
        })
        .catch((error) => {
          console.warn('[reminderService] getConfig failed, degrade to in-app', error)
          return DEFAULT_CONFIG
        })
        .finally(() => {
          loadingConfig = null
        })
    }
    return loadingConfig
  },

  /** 开启提醒：模板未就绪 / 非微信端 / 授权失败均降级为站内提醒 */
  async enable(): Promise<ReminderResult> {
    const config = await reminderService.getConfig()
    if (!isWeapp || !config.enabled || !config.templateId) {
      writeMirror(true)
      return { on: true, subscribed: false, message: '已开启站内提醒' }
    }
    if (prompted) {
      writeMirror(true)
      return { on: true, subscribed: false, message: '已开启提醒' }
    }
    prompted = true

    let result: Record<string, unknown>
    try {
      // Taro 4 的 Option 类型要求同时给出 tmplIds / entityIds 之一，空数组在微信端会被忽略
      const response = await Taro.requestSubscribeMessage({
        tmplIds: [config.templateId],
        entityIds: [],
      })
      result = response as unknown as Record<string, unknown>
    } catch (error) {
      console.warn('[reminderService] requestSubscribeMessage failed', error)
      writeMirror(true)
      return { on: true, subscribed: false, message: '已开启站内提醒' }
    }

    const accepted = result[config.templateId] === 'accept' ? 1 : 0
    if (accepted === 0) {
      writeMirror(false)
      return { on: false, subscribed: false, message: '未授权微信提醒' }
    }

    try {
      await request('/api/v1/reminder/subscription', {
        method: 'POST',
        data: { accepted, enabled: true },
      })
    } catch (error) {
      // 上报失败保留本地开关，不影响复习流程
      console.warn('[reminderService] report subscription failed', error)
    }

    writeMirror(true)
    return { on: true, subscribed: true, message: '已开启，每天 20:00 提醒你' }
  },

  /** 关闭提醒：本地立即生效，服务端上报失败不回滚 */
  async disable(): Promise<ReminderResult> {
    writeMirror(false)
    try {
      await request('/api/v1/reminder/subscription', {
        method: 'POST',
        data: { accepted: 0, enabled: false },
      })
    } catch (error) {
      console.warn('[reminderService] disable report failed', error)
    }
    return { on: false, subscribed: false, message: '已关闭微信提醒' }
  },
}
