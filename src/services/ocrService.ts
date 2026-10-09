import Taro from '@tarojs/taro'

import { OCR_API_BASE, OCR_ERROR_MESSAGES } from '@/constants'

export interface OcrResult {
  ok: boolean
  text: string
  wordsCount: number
  message?: string
}

interface OcrApiResponse {
  code: number
  text?: string
  wordsCount?: number
  message?: string
}

/**
 * OCR 流程编排：将压缩后的图片上传至 Python 后端代理，
 * 后端调用阿里云文字识别并返回清洗后的纯文本题干。
 * 失败/超时不阻断主流程，由编辑页兜底提示手动输入。
 */
export const ocrService = {
  async recognize(tempFilePath: string): Promise<OcrResult> {
    try {
      const res = await Taro.uploadFile({
        url: `${OCR_API_BASE}/api/v1/ocr`,
        filePath: tempFilePath,
        name: 'file',
        timeout: 30000,
      })

      const body = JSON.parse(res.data) as OcrApiResponse
      if (body.code === 0) {
        return { ok: true, text: body.text || '', wordsCount: body.wordsCount || 0 }
      }
      return {
        ok: false,
        text: '',
        wordsCount: 0,
        message: body.message || OCR_ERROR_MESSAGES[body.code] || '识别失败，请手动输入',
      }
    } catch (error) {
      console.error('[ocrService] recognize failed', error)
      return { ok: false, text: '', wordsCount: 0, message: '识别失败，请手动输入' }
    }
  },
}
