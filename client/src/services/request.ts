import Taro from "@tarojs/taro";

import {
  API_BASE,
  AUTH_CODE,
  AUTH_ERROR_MESSAGES,
  CONTENT_ERROR_MESSAGES,
  REQUEST_TIMEOUT,
} from "@/constants";
import type { AuthSession, UserProfile } from "@/types/user";

import { authRepo } from "./repo/authRepo";

/** 后端统一响应信封 */
interface ApiEnvelope<T> {
  code: number;
  message?: string;
  data?: T;
}

/** 登录/续期返回的数据体 */
export interface SessionData {
  accessToken: string;
  refreshToken: string;
  accessExpireAt: number;
  user: UserProfile;
}

export class ApiRequestError extends Error {
  code: number;

  constructor(code: number, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.code = code;
  }
}

export type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE";

export interface RequestOptions {
  method?: HttpMethod;
  data?: Record<string, unknown>;
  /** 是否携带 Authorization，默认 true */
  auth?: boolean;
}

function buildHeader(auth: boolean): Record<string, string> {
  const header: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const session = authRepo.getSession();
    if (session?.accessToken)
      header.Authorization = `Bearer ${session.accessToken}`;
  }
  return header;
}

function messageFor(code: number, fallback?: string): string {
  return (
    AUTH_ERROR_MESSAGES[code] ||
    CONTENT_ERROR_MESSAGES[code] ||
    fallback ||
    "网络异常，请稍后重试"
  );
}

/** 发一次请求，返回原始信封 */
async function send(
  path: string,
  options: RequestOptions,
): Promise<{ statusCode: number; body: ApiEnvelope<unknown> }> {
  try {
    const res = await Taro.request({
      url: `${API_BASE}${path}`,
      method: options.method || "GET",
      data: options.data,
      header: buildHeader(options.auth !== false),
      timeout: REQUEST_TIMEOUT,
    });
    return {
      statusCode: res.statusCode,
      body: (res.data || {}) as ApiEnvelope<unknown>,
    };
  } catch (error) {
    console.error("[request] network failed", path, error);
    throw new ApiRequestError(0, "网络异常，请检查网络后重试");
  }
}

function unwrap<T>(statusCode: number, body: ApiEnvelope<unknown>): T {
  if (body.code === 0) {
    return (body.data ?? {}) as T;
  }
  throw new ApiRequestError(
    body.code || statusCode,
    messageFor(body.code, body.message),
  );
}

/** 续期中的并发去重 */
let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const session = authRepo.getSession();
  if (!session?.refreshToken) return false;
  try {
    const res = await Taro.request({
      url: `${API_BASE}/api/v1/auth/refresh`,
      method: "POST",
      data: { refreshToken: session.refreshToken },
      header: { "Content-Type": "application/json" },
      timeout: REQUEST_TIMEOUT,
    });
    const body = (res.data || {}) as ApiEnvelope<SessionData>;
    if (res.statusCode === 200 && body.code === 0 && body.data) {
      const next: AuthSession = {
        accessToken: body.data.accessToken,
        refreshToken: body.data.refreshToken,
        accessExpireAt: body.data.accessExpireAt,
        user: body.data.user,
      };
      authRepo.saveSession(next);
      return true;
    }
  } catch (error) {
    console.error("[request] refresh failed", error);
  }
  authRepo.clearSession();
  return false;
}

function ensureRefreshed(): Promise<boolean> {
  if (!refreshing) {
    refreshing = doRefresh().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/**
 * 统一请求封装：注入 Authorization、解析信封、401 自动续期并重试一次。
 * 失败抛出 ApiRequestError（含业务 code）。
 */
export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const first = await send(path, options);

  const unauthorized =
    first.statusCode === 401 || first.body.code === AUTH_CODE.tokenInvalid;
  if (unauthorized && options.auth !== false) {
    const refreshed = await ensureRefreshed();
    if (refreshed) {
      const second = await send(path, options);
      return unwrap<T>(second.statusCode, second.body);
    }
    throw new ApiRequestError(
      AUTH_CODE.tokenInvalid,
      AUTH_ERROR_MESSAGES[AUTH_CODE.tokenInvalid],
    );
  }

  return unwrap<T>(first.statusCode, first.body);
}
