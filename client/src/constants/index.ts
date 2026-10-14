/** 本地存储 Key（对齐方案设计文档 §4.2） */
export const STORAGE_KEYS = {
  list: 'q:list',
  meta: 'q:meta',
  schema: 'q:schema',
  /** 登录态（token + 用户资料） */
  auth: 'u:auth',
  /** 本地删除墓碑，供云端同步删除 */
  removed: 'q:removed',
  /** 增量同步游标（上次同步的服务端时间，ms） */
  syncCursor: 'q:syncCursor',
  /** 是否已引导过「首次登录完善资料」 */
  nickPrompted: 'u:nickPrompted',
} as const

/** 当前数据结构版本 */
export const SCHEMA_VERSION = 1

/** 题库列表分页大小 */
export const PAGE_SIZE = 10

/**
 * 识别代理后端地址（Python FastAPI）。
 * - 必须使用「局域网 IP」：微信小程序网络层禁止访问「本机 IP / localhost」（127.0.0.1），
 *   该限制在开发者工具模拟器内同样生效，且勾选「不校验合法域名」也无法绕过，
 *   否则 uploadFile 会报 `createUploadTask:fail invalid url`。
 * - 模拟器与真机（手机与电脑同一 WiFi）均使用该局域网 IP。
 * - 开发机 IP 若因 DHCP 变化需同步修改此处；查询命令：
 *   Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' }
 *   （取「以太网」那一项，忽略 LetsTAP 等虚拟网卡）
 */
export const RECOGNIZE_API_BASE = 'http://192.168.60.37:8000'

/** 后端服务基地址（识别与账号体系共用同一服务） */
export const API_BASE = RECOGNIZE_API_BASE

/** 识别后端错误码文案 */
export const RECOGNIZE_ERROR_MESSAGES: Record<number, string> = {
  1002: '识别失败，请手动输入',
  1003: '识别额度受限，请稍后再试',
  1004: '图片无效或过大，请重新拍摄',
  1005: '识别服务未开通或无权限，请联系管理员',
}

/** 用户/鉴权错误码文案（2xxx） */
export const AUTH_ERROR_MESSAGES: Record<number, string> = {
  2001: '请先登录',
  2002: '登录已失效，请重新登录',
  2003: '登录服务暂不可用，请稍后再试',
  2004: '微信登录失败，请重试',
  2005: '参数有误，请检查后重试',
  2006: '头像文件无效或过大，请重新选择',
}

/** 鉴权相关错误码 */
export const AUTH_CODE = {
  unauthorized: 2001,
  tokenInvalid: 2002,
} as const

/** 题干最大字数 */
export const CONTENT_MAX_LENGTH = 200
/** 答案与解题过程最大字数 */
export const ANSWER_MAX_LENGTH = 600
/** 昵称最大字数（与服务端 32 上限保持前端更严格约束） */
export const NICKNAME_MAX_LENGTH = 20
/** 头像上传上限（字节），与服务端 AVATAR_MAX_BYTES 对齐 */
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024
/** 请求超时（ms） */
export const REQUEST_TIMEOUT = 15000
