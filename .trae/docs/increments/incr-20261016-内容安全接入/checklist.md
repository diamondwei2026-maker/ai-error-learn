# incr-20261016-内容安全接入 · 验收清单

> 图例：`[x]` 已自动验证（单测/构建）；`[ ]` 待上线环境人工验收

## 后端

- [x] `ContentSecurityService` 具备 access_token 缓存（提前 300s 失效）与 40001 重试一次
- [x] `ready == False` / 任意异常 / `errcode != 0` 时返回 `skipped`（文本）或 `None`（图片），从不上抛
- [x] `PATCH /user/me`：昵称命中 `risky` → `code 2007`，昵称未写入
- [x] `PATCH /user/me`：`review` / `skipped` → 正常写入
- [x] `POST /user/avatar`：`media_check_ready` 时才送检，并写 `media_check_record`
- [x] `POST /api/v1/security/text-check`：通过 `code 0`；命中 `code 3002`；未登录 `401 / 2001`；空文本不发远程调用
- [x] `POST /api/v1/sync/push`：仅对新增/`updatedAt` 变新且非墓碑项送检；命中入 `rejected` 且不落库
- [x] `POST /api/v1/sync/push`：响应新增 `rejected` 字段且旧字段保持兼容
- [x] `GET /api/v1/wechat/callback`：验签通过返回 `echostr` 明文；失败 `403`
- [x] `POST /api/v1/wechat/callback`：兼容 JSON/XML；`wxa_media_check` risky → 删头像文件 + 清空 `avatar_url`
- [x] 迟到回调不会误删用户新换的头像（按 `file_name` 二次校验）
- [x] 回调对未处理事件 / 未知 `trace_id` / 下载失败（`-1008`）均安全兜底并返回 `success`
- [x] `init_db()` 已登记新模型，新表可幂等创建

## 前端

- [x] `CONTENT_ERROR_MESSAGES` / `CONTENT_CODE` 与后端错误码一致
- [x] `messageFor()` 能解析 2007 / 3002
- [x] 保存错题前调用预检；命中 3002 → toast 且**不落库**、不跳转
- [x] 预检网络异常/服务异常 → 降级放行（继续本地保存）
- [x] 未登录态跳过预检，本地保存不受影响
- [x] `syncService` 对 `rejected` 记 `console.warn`，不删本地数据

## 回归

- [x] `server\.venv\Scripts\python.exe -m pytest` → **105 passed**，无回归
- [x] `npx tsc --noEmit` → 无新增类型错误
- [x] `npm run build:weapp` → 构建成功（exit 0）

## 上线前置（不阻塞编码，须人工操作）

- [ ] MP 后台 IP 白名单已加入 ECS 公网出口 IP（否则 `40164`）
- [ ] MP 后台「消息推送」URL / Token / 数据格式 JSON / 明文模式 已配置
- [ ] `.env` 已配置 `CONTENT_SECURITY_ENABLED` / `PUBLIC_BASE_URL` / `WECHAT_CALLBACK_TOKEN`
- [ ] `https://<域名>/static/avatars/*` 可被外网直接下载
- [ ] 真机验收：昵称违规拦截、错题保存拦截、断网降级放行、违规头像回调清除
