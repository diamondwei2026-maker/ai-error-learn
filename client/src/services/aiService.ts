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
  /** 已知学科：服务端按 questionId 查库优先，本字段为未同步时的兜底 */
  subject?: string;
  /** 已知题型（同上，库内缺失时兜底） */
  questionType?: string;
  /** 已知知识点（≤3 条，同上兜底） */
  knowledgePoints?: string[];
}

/** 举一反三：根据错题生成同构变式题（不入库、不排期） */
export const aiService = {
  async generateVariants(params: GenerateVariantsParams): Promise<AiVariantResult> {
    const data: Record<string, unknown> = {
      questionId: params.questionId || '',
      content: params.content,
      answer: params.answer || '',
    };
    // 仅在已有分类时提交，缺失不输出以保持旧协议语义
    if (params.subject) data.subject = params.subject;
    if (params.questionType) data.questionType = params.questionType;
    if (params.knowledgePoints?.length) {
      data.knowledgePoints = params.knowledgePoints;
    }
    try {
      return await request<AiVariantResult>('/api/v1/ai/variants', {
        method: 'POST',
        data,
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
