/** 本地存储 Key（对齐方案设计文档 §4.2） */
export const STORAGE_KEYS = {
  list: 'q:list',
  meta: 'q:meta',
  schema: 'q:schema',
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

/** 识别后端错误码文案 */
export const RECOGNIZE_ERROR_MESSAGES: Record<number, string> = {
  1002: '识别失败，请手动输入',
  1003: '识别额度受限，请稍后再试',
  1004: '图片无效或过大，请重新拍摄',
  1005: '识别服务未开通或无权限，请联系管理员',
}

/** 题干最大字数 */
export const CONTENT_MAX_LENGTH = 200
/** 答案与解题过程最大字数 */
export const ANSWER_MAX_LENGTH = 600
