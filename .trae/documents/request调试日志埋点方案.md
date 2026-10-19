# request.ts 调试日志埋点方案

> 类型：轻量增量（仅日志，无业务逻辑、无 UI、无后端改动）
> 目标文件：`client/src/services/request.ts`
> 适用场景：体验版真机排查「网络异常」时，需要看到请求的完整 URL、状态码、返回体与原始错误对象
> 说明：日志为**临时调试埋点**，问题定案后按标记统一删除

---

## 1. 背景与目标

当前 [request.ts](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L84-L87) 在网络失败时只打印了 `path`：

```ts
console.error("[request] network failed", path, error);
```

问题：

1. 不打印完整 URL，无法确认请求实际打到了哪个域名（本次排查中 `API_BASE` 出过两次问题）；
2. 不打印状态码与响应体，无法区分「网络层失败」「HTTP 非 200」「业务 code 非 0」；
3. 不打印请求方法、入参，无法复现；
4. 续期请求 `doRefresh()` 只有一条 `[request] refresh failed`，缺少上下文。

目标：在**不改变任何请求行为**的前提下，补充成功与失败两条调试日志。

---

## 2. 现状分析（基于实际代码）

| 位置 | 现状 | 说明 |
| --- | --- | --- |
| [send() L67-L88](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L67-L88) | 统一业务请求入口，内部已拼好 `${API_BASE}${path}` | 日志应加在此处，URL 可直接复用 |
| [doRefresh() L103-L130](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L103-L130) | 直接调用 `Taro.request`，未走 `send()` | 需单独加日志 |
| [unwrap() L90-L98](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L90-L98) | 业务 code 非 0 时抛 `ApiRequestError` | **本次不改**：成功日志已能打印出非 0 的 `body` |
| [request() L145-L166](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L145-L166) | 401 自动续期并重试一次 | 不改；重试会自然产生两条日志 |
| [prod.ts](file:///d:/Users/weij/ai-error-learn/client/config/prod.ts) | `mini: {}` / `h5: {}`，**未配置 `drop_console`** | 确认生产构建不会自动剔除 `console.log`，体验版可见 |
| [package.json L13](file:///d:/Users/weij/ai-error-learn/client/package.json#L13) | `build:weapp` 为生产构建 | 埋点会进入上传的 `dist/` |

**关键技术点**：`Taro.request` 的成功回调对象只有 `statusCode` / `data` / `header` / `errMsg`，**没有 `config` 和 `url` 字段**。因此需求示例中的 `response?.config?.url` 无法直接使用，必须用 `${API_BASE}${path}` 自行拼接。

---

## 3. 变更清单

> 只改 `client/src/services/request.ts` 一个文件。

### 3.1 新增模块级脱敏工具（约 25 行）

位置：`import` 之后、`interface ApiEnvelope` 之前（或紧邻 `buildHeader` 之后）。

```ts
/** 临时调试日志：需要脱敏的字段（小写比较） */
const SENSITIVE_KEYS = new Set([
  "authorization",
  "accesstoken",
  "refreshtoken",
  "token",
  "openid",
  "unionid",
]);

function maskValue(value: unknown): unknown {
  if (typeof value !== "string") return "***";
  if (value.length <= 8) return "***";
  return `${value.slice(0, 4)}***${value.slice(-4)}`;
}

/** 递归脱敏，限制深度与数组长度，避免同步接口日志过大 */
function sanitizeForLog(value: unknown, depth = 0): unknown {
  if (value === null || typeof value !== "object") return value;
  if (depth >= 3) return "[Object]";
  if (Array.isArray(value)) {
    return value.slice(0, 20).map((item) => sanitizeForLog(item, depth + 1));
  }
  const result: Record<string, unknown> = {};
  Object.entries(value as Record<string, unknown>).forEach(([key, item]) => {
    result[key] = SENSITIVE_KEYS.has(key.toLowerCase())
      ? maskValue(item)
      : sanitizeForLog(item, depth + 1);
  });
  return result;
}
```

**注意**：不要把 `code` 加入脱敏集合。后端统一信封里的 `code` 是数字业务码，加入后会把 `0` 显示成 `***`，反而影响判读；登录请求里的 `code` 是一次性临时凭证，保留原值对排查更有利。

### 3.2 `send()` 成功日志

在 `Taro.request` 返回后、`return` 之前插入：

```ts
console.log("【请求成功】", {
  url: `${API_BASE}${path}`,
  method: options.method || "GET",
  statusCode: res.statusCode,
  data: sanitizeForLog(res.data),
});
```

### 3.3 `send()` 失败日志

将现有 `console.error("[request] network failed", path, error);` **替换**为：

```ts
console.error("【请求详情/报错】", {
  url: `${API_BASE}${path}`,
  method: options.method || "GET",
  data: sanitizeForLog(options.data),
  status: undefined, // 网络层失败时没有 statusCode
  err: error,
});
```

保留后续 `throw new ApiRequestError(0, "网络异常，请检查网络后重试");` 不变。

### 3.4 `doRefresh()` 成功与失败日志

成功（拿到 `res` 后、判断 `body.code` 之前）：

```ts
console.log("【请求成功】", {
  url: `${API_BASE}/api/v1/auth/refresh`,
  method: "POST",
  statusCode: res.statusCode,
  data: sanitizeForLog(res.data),
});
```

失败：把 `console.error("[request] refresh failed", error);` 替换为：

```ts
console.error("【请求详情/报错】", {
  url: `${API_BASE}/api/v1/auth/refresh`,
  method: "POST",
  data: sanitizeForLog({ refreshToken: session.refreshToken }),
  status: undefined,
  err: error,
});
```

### 3.5 明确不改动的部分

- `unwrap()` 的业务错误处理逻辑；
- `request()` 的 401 续期与重试流程；
- `buildHeader()`、`messageFor()`；
- 其他 service（`authService` / `userService` / `syncService` / `recognitionService`）的日志；
- 后端、nginx、`dist` 的既有内容。

### 3.6 临时标记

在上述新增日志旁统一加一行注释，便于定案后全局检索删除：

```ts
// TODO(debug-request): 临时调试日志，排查结束后删除
```

---

## 4. 关键决策与假设（均已与用户确认）

| 决策 | 选择 | 说明 |
| --- | --- | --- |
| 生效范围 | **所有构建都输出** | 无 `NODE_ENV` 守卫；体验版是生产构建，必须能看日志 |
| 敏感字段 | **脱敏后再打印** | `Authorization`、`accessToken`、`refreshToken`、`token`、`openid`、`unionid` |
| 覆盖范围 | **业务请求 + 续期请求** | `send()` 与 `doRefresh()` 两处 |
| URL 来源 | 自行拼接 `${API_BASE}${path}` | Taro 成功响应没有 `config.url` |
| 日志标签 | 固定 `【请求成功】` / `【请求详情/报错】` | 便于 vConsole 检索与后续删除 |
| 业务错误码 | 不在 `unwrap()` 单独加日志 | 成功日志已打印 `statusCode` 与 `body.code` |

**假设**：

1. 生产构建不会剔除 `console.*`（`prod.ts` 未配置 `drop_console`，且现有 `[config]` 守卫日志已证实会进产物）。
2. `Taro.request` 失败时抛出的对象包含 `errMsg`（微信端还会带 `errno` / `errcode`），原样传入 `err` 即可，不做二次加工。
3. 同步接口 `items` 数组可能较大，脱敏工具限制数组前 20 条、递归深度 3 层，避免 vConsole 卡顿。

---

## 5. 验证步骤

```powershell
cd d:\Users\weij\ai-error-learn\client
npx tsc --noEmit
npm run build:weapp
```

验收点：

1. `tsc --noEmit` 在 `src/` 下无新增错误（允许 `node_modules/@tarojs/components/*.d.ts` 既有报错）。
2. `npm run build:weapp` 退出码 0。
3. 产物中存在日志标签，证明未被压缩剔除：

```powershell
Select-String -Path .\dist\common.js -Pattern "【请求成功】" -SimpleMatch
Select-String -Path .\dist\common.js -Pattern "【请求详情/报错】" -SimpleMatch
```

4. 微信开发者工具模拟器点「微信一键登录」：
   - 正常时 Console 出现 `【请求成功】`，`url` 为 `https://errorlearn.diamondwtech.com/api/v1/auth/login`；
   - 断网或改错域名时出现 `【请求详情/报错】`，`err.errMsg` 可读。
5. 真机体验版（vConsole）点登录，确认能看到同一条日志与完整 URL。
6. 脱敏校验：成功响应中的 `accessToken` 应显示为形如 `eyJh***abcd`，`Authorization` 请求头不出现在日志里。

---

## 6. 回滚方式

- 删除 3.2 / 3.3 / 3.4 三处日志与 3.1 的两个工具函数；
- 或直接 `git checkout -- client/src/services/request.ts`（本次只改这一个文件）；
- 产物重新执行 `npm run build:weapp` 覆盖 `dist/`。

---

## 7. 风险与提示

| 风险 | 处理 |
| --- | --- |
| 日志进入生产包 | 属于本次有意为之（体验版排查需要）；上线前必须按 `TODO(debug-request)` 标记删除 |
| 用户数据出现在 vConsole | 已脱敏 token 与 openid；昵称、题干等业务数据仍会打印，仅供开发者本机排查 |
| 同步接口日志偏大 | 数组截断 20 条、深度 3 层 |
| 日志量增加 | 仅在 `send()` 与 `doRefresh()` 两处，且每次请求两条以内 |

---

## 8. 与主 spec 的关系

- 属于**临时调试埋点**，不改变任何业务行为，不新增页面、不涉及 UI；
- **不修改** `.trae/specs/mvp-reverse-docs/`；
- 定案后需在 `.trae/docs/change-log.md` 追加一条临时记录（或与本次 -101 排查结论合并记录）。
