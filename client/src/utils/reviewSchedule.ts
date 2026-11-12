import type { Question } from "@/types/question";

/** 艾宾浩斯复习间隔（天），下标对应轮次 1..6 */
export const REVIEW_INTERVALS_DAYS = [1, 2, 4, 7, 15, 30] as const;

/** 有效轮次上限，超过即视为已掌握 */
export const MAX_STAGE = REVIEW_INTERVALS_DAYS.length;

const DAY_MS = 24 * 60 * 60 * 1000;

/** 自评结果 */
export type ReviewRating = "remembered" | "forgot";

/** 排期结果 */
export interface ReviewSchedule {
  reviewStage: number;
  /** null 表示已掌握、不再进入队列 */
  nextReviewAt: number | null;
}

/** 当天 00:00 的时间戳 */
export function startOfDay(ts: number): number {
  const date = new Date(ts);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

/** 当天 23:59:59.999 的时间戳 */
export function endOfDay(ts: number): number {
  return startOfDay(ts) + DAY_MS - 1;
}

function startOfDayAfter(ts: number, days: number): number {
  return startOfDay(ts) + days * DAY_MS;
}

/** 新入库题目的初始排期：第 1 轮，次日 00:00 到期 */
export function initSchedule(now: number = Date.now()): ReviewSchedule {
  return {
    reviewStage: 1,
    nextReviewAt: startOfDayAfter(now, REVIEW_INTERVALS_DAYS[0]),
  };
}

/**
 * 按自评结果推进轮次并计算下次到期时间。
 * - 记住了：轮次 +1，间隔取新轮次的天数；超过 6 轮视为已掌握（nextReviewAt = null）
 * - 没记住：轮次 -1（最低 1），间隔取回退后轮次的天数
 */
export function calcNextReview(
  stage: number,
  rating: ReviewRating,
  now: number = Date.now(),
): ReviewSchedule {
  const current = Math.min(
    Math.max(Number.isFinite(stage) ? Math.floor(stage) : 1, 1),
    MAX_STAGE,
  );

  if (rating === "remembered") {
    const nextStage = current + 1;
    if (nextStage > MAX_STAGE) {
      return { reviewStage: nextStage, nextReviewAt: null };
    }
    return {
      reviewStage: nextStage,
      nextReviewAt: startOfDayAfter(now, REVIEW_INTERVALS_DAYS[nextStage - 1]),
    };
  }

  const nextStage = Math.max(1, current - 1);
  return {
    reviewStage: nextStage,
    nextReviewAt: startOfDayAfter(now, REVIEW_INTERVALS_DAYS[nextStage - 1]),
  };
}

/** 是否到期（含逾期）；未排期或已掌握均不算到期 */
export function isDue(
  question: Pick<Question, "nextReviewAt">,
  now: number = Date.now(),
): boolean {
  if (typeof question.nextReviewAt !== "number") return false;
  return question.nextReviewAt <= endOfDay(now);
}

/** 到期队列：按到期日升序（逾期最久优先），同日按创建时间升序 */
export function sortDue(list: Question[], now: number = Date.now()): Question[] {
  return list
    .filter((item) => isDue(item, now))
    .sort((a, b) => {
      const diff = (a.nextReviewAt as number) - (b.nextReviewAt as number);
      return diff !== 0 ? diff : a.createdAt - b.createdAt;
    });
}

/** 首页今日待复习摘要 */
export interface DueSummary {
  /** 到期题数 */
  count: number;
  /** 最早一笔的逾期天数（0 表示今日到期） */
  overdueDays: number;
  /** 预计耗时（分钟，每题按 30s 估算） */
  estimatedMinutes: number;
  /** 涉及的最小轮次，无到期为 null */
  stageMin: number | null;
  /** 涉及的最大轮次，无到期为 null */
  stageMax: number | null;
}

export function dueSummary(
  list: Question[],
  now: number = Date.now(),
): DueSummary {
  const due = sortDue(list, now);
  if (!due.length) {
    return {
      count: 0,
      overdueDays: 0,
      estimatedMinutes: 0,
      stageMin: null,
      stageMax: null,
    };
  }

  const stages = due.map((item) => item.reviewStage ?? 1);
  const earliestAt = due[0].nextReviewAt as number;

  return {
    count: due.length,
    overdueDays: Math.max(
      0,
      Math.floor((startOfDay(now) - startOfDay(earliestAt)) / DAY_MS),
    ),
    estimatedMinutes: Math.ceil((due.length * 30) / 60),
    stageMin: Math.min(...stages),
    stageMax: Math.max(...stages),
  };
}

/** 下次到期信息 */
export interface NextDueInfo {
  /** 下次到期日 00:00；无后续排期为 null */
  at: number | null;
  /** 同一天到期的题数 */
  count: number;
  /** 距今天数（至少 1） */
  daysUntil: number;
}

export function nextDueInfo(
  list: Question[],
  now: number = Date.now(),
): NextDueInfo {
  const todayEnd = endOfDay(now);
  const upcoming = list.filter(
    (item) => typeof item.nextReviewAt === "number" && item.nextReviewAt > todayEnd,
  );
  if (!upcoming.length) return { at: null, count: 0, daysUntil: 0 };

  const at = Math.min(...upcoming.map((item) => item.nextReviewAt as number));
  return {
    at,
    count: upcoming.filter((item) => item.nextReviewAt === at).length,
    daysUntil: Math.max(
      1,
      Math.round((startOfDay(at) - startOfDay(now)) / DAY_MS),
    ),
  };
}
