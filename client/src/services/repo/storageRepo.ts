import Taro from '@tarojs/taro'

import { SCHEMA_VERSION, STORAGE_KEYS } from '@/constants'
import type { AppMeta, Question } from '@/types/question'

const DEFAULT_META: AppMeta = {
  schemaVersion: SCHEMA_VERSION,
  imageBytes: 0,
  questionCount: 0,
}

/**
 * 数据访问层：封装 Storage 读写细节。
 * 页面与业务服务一律通过本模块访问存储，禁止直接调用 Taro.setStorage。
 */
export const storageRepo = {
  listQuestions(): Question[] {
    try {
      const raw = Taro.getStorageSync(STORAGE_KEYS.list)
      return Array.isArray(raw) ? (raw as Question[]) : []
    } catch (error) {
      console.error('[storageRepo] listQuestions failed', error)
      return []
    }
  },

  saveQuestions(list: Question[]): void {
    try {
      Taro.setStorageSync(STORAGE_KEYS.list, list)
    } catch (error) {
      console.error('[storageRepo] saveQuestions failed', error)
      throw error
    }
  },

  getMeta(): AppMeta {
    try {
      const raw = Taro.getStorageSync(STORAGE_KEYS.meta)
      if (raw && typeof raw === 'object') {
        return { ...DEFAULT_META, ...(raw as Partial<AppMeta>) }
      }
    } catch (error) {
      console.error('[storageRepo] getMeta failed', error)
    }
    return { ...DEFAULT_META }
  },

  saveMeta(meta: AppMeta): void {
    try {
      Taro.setStorageSync(STORAGE_KEYS.meta, meta)
      Taro.setStorageSync(STORAGE_KEYS.schema, meta.schemaVersion)
    } catch (error) {
      console.error('[storageRepo] saveMeta failed', error)
    }
  },
}
