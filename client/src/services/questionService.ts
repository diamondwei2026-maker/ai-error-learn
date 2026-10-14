import { PAGE_SIZE, SCHEMA_VERSION } from '@/constants'
import { createId } from '@/utils/id'
import type { Question } from '@/types/question'

import { authRepo } from './repo/authRepo'
import { fileRepo } from './repo/fileRepo'
import { storageRepo } from './repo/storageRepo'
import { syncService } from './syncService'

export interface CreateQuestionInput {
  content: string
  answer: string
  /** 已压缩的临时图片路径 */
  tempImagePath?: string
}

/** 本轮已抽题 ID 集合（保证一轮内不重复） */
let roundDrawn: string[] = []

function sortByCreatedDesc(list: Question[]): Question[] {
  return [...list].sort((a, b) => b.createdAt - a.createdAt)
}

function fisherYates<T>(input: T[]): T[] {
  const arr = [...input]
  for (let i = arr.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    const tmp = arr[i]
    arr[i] = arr[j]
    arr[j] = tmp
  }
  return arr
}

/**
 * 错题业务编排：录入、查询、删除、随机抽题。
 * 仅通过 repo 层访问存储，页面不直接操作 Storage。
 */
export const questionService = {
  /** 新建错题：先落图片，再写列表与元数据 */
  async create(input: CreateQuestionInput): Promise<Question> {
    const id = createId()
    let imagePath: string | undefined
    let imageSize = 0

    if (input.tempImagePath) {
      const saved = await fileRepo.saveImage(input.tempImagePath, id)
      imagePath = saved.path
      imageSize = saved.size
    }

    const now = Date.now()
    const question: Question = {
      id,
      content: input.content.trim(),
      answer: (input.answer || '').trim(),
      imagePath,
      imageSize: imageSize || undefined,
      createdAt: now,
      updatedAt: now,
    }

    const list = storageRepo.listQuestions()
    list.unshift(question)
    storageRepo.saveQuestions(list)

    const meta = storageRepo.getMeta()
    storageRepo.saveMeta({
      schemaVersion: SCHEMA_VERSION,
      questionCount: list.length,
      imageBytes: meta.imageBytes + imageSize,
    })

    // 登录态下异步镜像到云端（节流，失败静默）
    syncService.scheduleSync()

    return question
  },

  /** 分页查询（按创建时间倒序），page 从 1 开始 */
  list(page: number, size: number = PAGE_SIZE): Question[] {
    const sorted = sortByCreatedDesc(storageRepo.listQuestions())
    const start = Math.max(0, (page - 1) * size)
    return sorted.slice(start, start + size)
  },

  /** 全量列表（倒序） */
  all(): Question[] {
    return sortByCreatedDesc(storageRepo.listQuestions())
  },

  get(id: string): Question | undefined {
    return storageRepo.listQuestions().find((item) => item.id === id)
  },

  /** 删除错题，并同步清理原图与元数据 */
  async remove(id: string): Promise<void> {
    const list = storageRepo.listQuestions()
    const target = list.find((item) => item.id === id)
    if (!target) return

    fileRepo.removeImage(target.imagePath)

    const next = list.filter((item) => item.id !== id)
    storageRepo.saveQuestions(next)

    const meta = storageRepo.getMeta()
    storageRepo.saveMeta({
      schemaVersion: SCHEMA_VERSION,
      questionCount: next.length,
      imageBytes: Math.max(0, meta.imageBytes - (target.imageSize || 0)),
    })

    roundDrawn = roundDrawn.filter((drawnId) => drawnId !== id)

    // 记录删除墓碑，供云端同步删除；并触发一次后台同步
    authRepo.addTombstone(id)
    syncService.scheduleSync()
  },

  /** 随机抽题：Fisher-Yates 洗牌 + 本轮已抽集合，抽完一轮自动重置 */
  pickRandom(excludeIds: string[] = []): Question | undefined {
    const all = storageRepo.listQuestions()
    if (all.length === 0) return undefined

    let pool = all.filter((item) => !roundDrawn.includes(item.id))
    if (pool.length === 0) {
      roundDrawn = []
      pool = [...all]
    }

    const excluded = new Set(excludeIds)
    let candidates = pool.filter((item) => !excluded.has(item.id))
    if (candidates.length === 0) candidates = fisherYates(pool)
    else candidates = fisherYates(candidates)

    const picked = candidates[0]
    roundDrawn.push(picked.id)
    return picked
  },

  /** 重置本轮抽题集合 */
  resetRound(): void {
    roundDrawn = []
  },

  /** 本轮已抽题数 */
  roundDrawnCount(): number {
    return roundDrawn.length
  },

  count(): number {
    return storageRepo.listQuestions().length
  },
}
