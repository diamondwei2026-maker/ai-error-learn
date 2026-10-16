/** 本地存储 Key（对齐方案设计文档 §4.2） */
export const STORAGE_KEYS = {
  list: "q:list",
  meta: "q:meta",
  schema: "q:schema",
  /** 登录态（token + 用户资料） */
  auth: "u:auth",
  /** 本地删除墓碑，供云端同步删除 */
  removed: "q:removed",
  /** 增量同步游标（上次同步的服务端时间，ms） */
  syncCursor: "q:syncCursor",
  /** 是否已引导过「首次登录完善资料」 */
  nickPrompted: "u:nickPrompted",
} as const;

/** 当前数据结构版本 */
export const SCHEMA_VERSION = 1;

/** 题库列表分页大小 */
export const PAGE_SIZE = 10;

/**
 * 后端服务基地址（识别与账号体系共用同一服务）。
 * 由构建期环境变量 `TARO_APP_API_BASE` 注入（见 `client/.env.development` / `.env.production`）：
 * - 开发/联调：局域网 IP（如 http://192.168.60.37:8000），模拟器与真机（同一 WiFi）均使用；
 * - 生产：已备案的 HTTPS 域名（如 https://api.example.com）。
 * 注意：微信小程序网络层禁止访问 localhost / 127.0.0.1；生产必须使用 HTTPS 域名，
 * 且需在微信公众平台配置 request / uploadFile / downloadFile 合法域名。
 */
export const API_BASE =
  process.env.TARO_APP_API_BASE || "http://192.168.60.37:8000";

// 防复发：误用生产构建（npm run build:weapp）做本地联调时，API_BASE 会指向占位域名，
// 表现为登录/识别报「网络异常」（ERR_NAME_NOT_RESOLVED）。此处显式告警，便于快速定位。
if (API_BASE.includes("api.example.com")) {
  console.error(
    "[config] API_BASE 仍为占位域名 api.example.com：开发联调请用 npm run dev:weapp；生产部署请先在 .env.production 配置真实域名",
  );
}

// 防复发：生产构建若指向局域网 IP / HTTP（如误用 dev 构建产物上传体验版/正式版），
// 真机上微信会强制校验合法域名，请求直接在网络层失败，表现为「网络异常」。
if (
  process.env.NODE_ENV === "production" &&
  !/^https:\/\/[a-z0-9.-]+\.[a-z]{2,}$/i.test(API_BASE)
) {
  console.error(
    `[config] 生产构建的 API_BASE 非法：${API_BASE}（须为 HTTPS 公网域名），请检查 client/.env.production`,
  );
}

/** 识别代理后端地址（与账号体系共用同一服务，保留旧导出名以兼容既有引用） */
export const RECOGNIZE_API_BASE = API_BASE;

/** 识别后端错误码文案 */
export const RECOGNIZE_ERROR_MESSAGES: Record<number, string> = {
  1002: "识别失败，请手动输入",
  1003: "识别额度受限，请稍后再试",
  1004: "图片无效或过大，请重新拍摄",
  1005: "识别服务未开通或无权限，请联系管理员",
};

/** 用户/鉴权错误码文案（2xxx） */
export const AUTH_ERROR_MESSAGES: Record<number, string> = {
  2001: "请先登录",
  2002: "登录已失效，请重新登录",
  2003: "登录服务暂不可用，请稍后再试",
  2004: "微信登录失败，请重试",
  2005: "参数有误，请检查后重试",
  2006: "头像文件无效或过大，请重新选择",
};

/** 鉴权相关错误码 */
export const AUTH_CODE = {
  unauthorized: 2001,
  tokenInvalid: 2002,
} as const;

/** 内容安全错误码（与后端 server/app/errors.py 保持一致） */
export const CONTENT_CODE = {
  /** 昵称命中违规 */
  nicknameRisky: 2007,
  /** 错题题干/答案命中违规 */
  questionRisky: 3002,
} as const;

/** 内容安全错误码文案 */
export const CONTENT_ERROR_MESSAGES: Record<number, string> = {
  [CONTENT_CODE.nicknameRisky]: "昵称包含违规内容，请修改后重试",
  [CONTENT_CODE.questionRisky]: "题干或答案包含违规内容，请修改后重试",
};

/** 协议类型（协议页通过 query 区分，见 AGREEMENT_PAGE_PATH） */
export const AGREEMENT_TYPE = {
  privacy: "privacy",
  terms: "terms",
} as const;

export type AgreementType =
  (typeof AGREEMENT_TYPE)[keyof typeof AGREEMENT_TYPE];

/** 协议页路径 */
export const AGREEMENT_PAGE_PATH = "/pages/agreement/index";

/** 协议页标题映射 */
export const AGREEMENT_TITLES: Record<string, string> = {
  [AGREEMENT_TYPE.privacy]: "隐私政策",
  [AGREEMENT_TYPE.terms]: "用户协议",
};

/** 用户拒绝隐私授权时的提示文案 */
export const PRIVACY_DENIED_MESSAGE = "需同意隐私授权后才能使用该功能";

/** 题干最大字数 */
export const CONTENT_MAX_LENGTH = 200;
/** 答案与解题过程最大字数 */
export const ANSWER_MAX_LENGTH = 600;
/** 昵称最大字数（与服务端 32 上限保持前端更严格约束） */
export const NICKNAME_MAX_LENGTH = 20;
/** 头像上传上限（字节），与服务端 AVATAR_MAX_BYTES 对齐 */
export const AVATAR_MAX_BYTES = 2 * 1024 * 1024;
/** 请求超时（ms） */
export const REQUEST_TIMEOUT = 15000;
