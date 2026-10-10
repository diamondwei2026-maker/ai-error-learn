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
 * OCR 代理后端地址（Python FastAPI）。
 * 真机调试时改为局域网 IP 或已备案的 HTTPS 域名。
 */
export const OCR_API_BASE = 'http://127.0.0.1:8000'

/** OCR 后端错误码文案 */
export const OCR_ERROR_MESSAGES: Record<number, string> = {
  1001: '图片加载失败，请重试',
  1002: '识别失败，请手动输入',
  1003: '识别额度受限，请稍后再试',
  1004: '图片无效或过大，请重新拍摄',
  1005: 'OCR 服务未开通或无权限，请联系管理员',
}

/** 题干最大字数 */
export const CONTENT_MAX_LENGTH = 200
/** 答案最大字数 */
export const ANSWER_MAX_LENGTH = 300
