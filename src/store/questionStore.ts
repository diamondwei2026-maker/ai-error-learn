import { create } from 'zustand'

import { questionService } from '@/services/questionService'

interface QuestionState {
  /** 错题总数（冗余缓存，加速首页/题库展示） */
  total: number
  /** 从本地存储重新计算并在页面间同步 */
  refresh: () => void
}

export const useQuestionStore = create<QuestionState>((set) => ({
  total: 0,
  refresh: () => {
    const total = questionService.count()
    console.info('[questionStore] refresh total =', total)
    set({ total })
  },
}))
