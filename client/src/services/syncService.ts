import { SCHEMA_VERSION } from "@/constants";
import type { Question } from "@/types/question";
import type { SyncItem, Tombstone } from "@/types/user";

import { request } from "./request";
import { authRepo } from "./repo/authRepo";
import { fileRepo } from "./repo/fileRepo";
import { storageRepo } from "./repo/storageRepo";

/** 本地写入后触发同步的节流间隔 */
const SYNC_THROTTLE_MS = 3000;

let throttleTimer: ReturnType<typeof setTimeout> | null = null;
let syncing = false;

interface PushResult {
  accepted: string[];
  /** 被服务端内容安全兜底拦截的 id（不落库） */
  rejected?: string[];
  serverTime: number;
}

interface PullResult {
  items: SyncItem[];
  serverTime: number;
}

function questionToItem(question: Question): SyncItem {
  return {
    id: question.id,
    content: question.content,
    answer: question.answer,
    createdAt: question.createdAt,
    updatedAt: question.updatedAt,
    deleted: false,
  };
}

function tombstoneToItem(tombstone: Tombstone): SyncItem {
  return {
    id: tombstone.id,
    content: "",
    answer: "",
    createdAt: tombstone.updatedAt,
    updatedAt: tombstone.updatedAt,
    deleted: true,
  };
}

/** 待上行数据 = 本地错题 + 本地删除墓碑 */
function collectLocalItems(): SyncItem[] {
  const questions = storageRepo.listQuestions().map(questionToItem);
  const tombstones = authRepo.listTombstones().map(tombstoneToItem);
  return [...questions, ...tombstones];
}

/** 合并云端增量到本地（updatedAt 新者优先；墓碑删除） */
function mergeRemoteItems(items: SyncItem[]): void {
  if (!items.length) return;

  const byId = new Map(
    storageRepo.listQuestions().map((item) => [item.id, item]),
  );
  let changed = false;
  let imageBytesDelta = 0;

  items.forEach((remote) => {
    const local = byId.get(remote.id);

    if (remote.deleted) {
      if (local) {
        fileRepo.removeImage(local.imagePath);
        imageBytesDelta -= local.imageSize || 0;
        byId.delete(remote.id);
        changed = true;
      }
      authRepo.removeTombstone(remote.id);
      return;
    }

    if (!local) {
      // 云端新增：仅文本，无原图
      byId.set(remote.id, {
        id: remote.id,
        content: remote.content,
        answer: remote.answer,
        createdAt: remote.createdAt,
        updatedAt: remote.updatedAt,
      });
      changed = true;
      return;
    }

    if (remote.updatedAt > local.updatedAt) {
      byId.set(remote.id, {
        ...local,
        content: remote.content,
        answer: remote.answer,
        updatedAt: remote.updatedAt,
      });
      changed = true;
    }
  });

  if (!changed) return;

  const next = [...byId.values()];
  storageRepo.saveQuestions(next);
  const meta = storageRepo.getMeta();
  storageRepo.saveMeta({
    schemaVersion: SCHEMA_VERSION,
    questionCount: next.length,
    imageBytes: Math.max(0, meta.imageBytes + imageBytesDelta),
  });
  console.info("[syncService] merged remote items, local total =", next.length);
}

async function syncNow(): Promise<void> {
  const session = authRepo.getSession();
  if (!session || syncing) return;

  syncing = true;
  try {
    const cursor = authRepo.getSyncCursor();

    const pushed = await request<PushResult>("/api/v1/sync/push", {
      method: "POST",
      data: { items: collectLocalItems(), cursor },
    });
    if (pushed.rejected?.length) {
      // 服务端内容安全兜底拦截：未落库；本地保留不删除，仅记录，避免反复重试打扰
      console.warn(
        "[syncService] rejected by content security:",
        pushed.rejected,
      );
    }
    // 上行成功后才清理墓碑，避免失败时丢失删除意图
    authRepo.saveTombstones([]);

    const pulled = await request<PullResult>(
      `/api/v1/sync/pull?since=${cursor}`,
    );
    mergeRemoteItems(pulled.items);

    authRepo.setSyncCursor(
      Math.max(cursor, pushed.serverTime, pulled.serverTime),
    );
    console.info("[syncService] sync done, cursor =", pulled.serverTime);
  } catch (error) {
    // 同步失败不影响本地使用，下次启动/写入时静默重试
    console.error("[syncService] sync failed", error);
  } finally {
    syncing = false;
  }
}

/** 节流触发一次后台同步（仅在登录态生效） */
function scheduleSync(): void {
  if (!authRepo.getSession()) return;
  if (throttleTimer) clearTimeout(throttleTimer);
  throttleTimer = setTimeout(() => {
    throttleTimer = null;
    void syncNow();
  }, SYNC_THROTTLE_MS);
}

/** 云端同步编排：登录后自动执行，用户无感知。 */
export const syncService = {
  syncNow,
  scheduleSync,
};
