import Taro from '@tarojs/taro'

import { RECOGNIZE_API_BASE, RECOGNIZE_ERROR_MESSAGES } from '@/constants'

/** 答案来源：vlm=多模态识别 / none=未识别到答案 */
export type SplitMethod = 'vlm' | 'none'

export interface RecognitionResult {
  ok: boolean
  /** 题干 */
  text: string
  /** 自动识别出的答案（可为空） */
  answer: string
  /** 答案来源：vlm=多模态识别 / none=未识别 */
  splitMethod: SplitMethod
  wordsCount: number
  message?: string
}

interface RecognizeApiResponse {
  code: number
  text?: string
  answer?: string
  splitMethod?: string
  wordsCount?: number
  message?: string
}

function toSplitMethod(raw?: string): SplitMethod {
  return raw === 'vlm' ? 'vlm' : 'none'
}

/**
 * 识别流程编排：将压缩后的图片上传至 Python 后端代理，
 * 后端调用多模态大模型一步识别题干与答案。
 * 失败/超时不阻断主流程，由编辑页兜底提示手动输入。
 */
export const recognitionService = {
  async recognize(tempFilePath: string): Promise<RecognitionResult> {
    try {
      const res = await Taro.uploadFile({
        url: `${RECOGNIZE_API_BASE}/api/v1/recognize`,
        filePath: tempFilePath,
        name: 'file',
        timeout: 30000,
      })

      const body = JSON.parse(res.data) as RecognizeApiResponse
      if (body.code === 0) {
        return {
          ok: true,
          text: body.text || '',
          answer: body.answer || '',
          splitMethod: toSplitMethod(body.splitMethod),
          wordsCount: body.wordsCount || 0,
        }
      }
      return {
        ok: false,
        text: '',
        answer: '',
        splitMethod: 'none',
        wordsCount: 0,
        message: body.message || RECOGNIZE_ERROR_MESSAGES[body.code] || '识别失败，请手动输入',
      }
    } catch (error) {
      console.error('[recognitionService] recognize failed', error)
      return { ok: false, text: '', answer: '', splitMethod: 'none', wordsCount: 0, message: '识别失败，请手动输入' }
    }
  },
}
