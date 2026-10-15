import { create } from 'zustand'

/**
 * 微信 onNeedPrivacyAuthorization 的 resolve 回调。
 * 调用后告知平台用户的选择，被拦截的隐私接口才会继续执行或失败返回。
 */
export type PrivacyResolve = (option: {
  event: 'exposureAuthorization' | 'agree' | 'disagree'
  buttonId?: string
}) => void

/** 隐私弹层「同意」按钮的 id（微信会校验该按钮是否真被点击过） */
export const AGREE_BUTTON_ID = 'agree-privacy-btn'

interface PrivacyState {
  /** 弹层是否可见 */
  visible: boolean
  /** 微信侧记录的《用户隐私保护指引》名称（用于展示入口文案） */
  contractName: string
  /** 因隐私接口被拦截而待 resolve 的回调队列（支持多接口并发） */
  pending: PrivacyResolve[]
  /** 打开弹层：resolve 由「隐私接口被拦截」时注入；「启动主动查询」时传 null */
  open: (resolve?: PrivacyResolve | null, contractName?: string) => void
  /** 用户点击「同意并继续」 */
  agree: () => void
  /** 用户点击「暂不授权」 */
  disagree: () => void
}

/**
 * 隐私授权弹层状态。
 * 单例控制 visible，避免同页面多隐私接口并发时弹层叠加。
 */
export const usePrivacyStore = create<PrivacyState>((set, get) => ({
  visible: false,
  contractName: '',
  pending: [],

  open: (resolve, contractName) =>
    set((state) => ({
      visible: true,
      contractName: contractName || state.contractName,
      pending: resolve ? [...state.pending, resolve] : state.pending,
    })),

  agree: () => {
    // 必须 resolve 队列中的每个回调，否则被拦截的隐私接口会一直 pending
    get().pending.forEach((resolve) => resolve({ event: 'agree', buttonId: AGREE_BUTTON_ID }))
    set({ visible: false, pending: [] })
  },

  disagree: () => {
    get().pending.forEach((resolve) => resolve({ event: 'disagree' }))
    set({ visible: false, pending: [] })
  },
}))
