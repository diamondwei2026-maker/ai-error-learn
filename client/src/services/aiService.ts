import { AI_ERROR_MESSAGES, AI_REQUEST_TIMEOUT } from '@/constants';

import { ApiRequestError, request } from './request';

/** 单道变式题 */
export interface AiVariant {
  stem: string;
  answer: string;
}

/** 变式题生成结果 */
export interface AiVariantResult {
  subject: string;
  questionType: string;
  knowledgePoints: string[];
  variants: AiVariant[];
  traceId?: string;
}

export interface GenerateVariantsParams {
  /** 原题 id，仅用于服务端日志追踪 */
  questionId?: string;
  /** 原题题干（1..2000 字） */
  content: string;
  /** 原题答案/解答（0..4000 字） */
  answer?: string;
}

/** 举一反三：根据错题生成同构变式题（不入库、不排期） */
export const aiService = {
  async generateVariants(params: GenerateVariantsParams): Promise<AiVariantResult> {
    try {
      return await request<AiVariantResult>('/api/v1/ai/variants', {
        method: 'POST',
        data: {
          questionId: params.questionId || '',
          content: params.content,
          answer: params.answer || '',
        },
        timeout: AI_REQUEST_TIMEOUT,
      });
    } catch (error) {
      if (error instanceof ApiRequestError) {
        throw new ApiRequestError(
          error.code,
          AI_ERROR_MESSAGES[error.code] || error.message,
        );
      }
      throw error;
    }
  },
};
