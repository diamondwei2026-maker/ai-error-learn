import { request } from './request'

export interface TextCheckInput {
  content: string
  answer?: string
}

/** 内容安全：错题内容保存前预检（与服务端 sync/push 兜底同一口径）。 */
export const securityService = {
  /**
   * 预检题干与答案。通过则正常返回；命中违规抛 ApiRequestError(code = 3002)；
   * 服务端降级放行时同样返回成功。
   */
  async checkQuestionText(input: TextCheckInput): Promise<void> {
    await request<{ pass: boolean }>('/api/v1/security/text-check', {
      method: 'POST',
      data: { content: input.content, answer: input.answer || '' },
    })
  },
}
