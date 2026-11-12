# 开发任务清单 · 艾宾浩斯复习提醒

- 增量编号：incr-20261111-复习提醒
- 日期：2026-11-11
- 阶段：阶段四（风险评估与任务拆解）
- 依据：`研讨记录.md`（5 项决策已收敛）、`主基线固化更新报告.md`（基线已确认）
- 视觉真值：`.trae/prototypes/错题本/错题本原型-01-录入与入库.html`、`错题本原型-03-刷题复习.html`
- 增量原型（溯源）：`prototype/visual/复习提醒-视觉.html`
- 管控方式：**按 spec 级管控**（涉及数据模型 + 前后端跨模块），但文档仅落在本增量目录，**不修改主 spec**

---

## 一、影响范围评估

### 1.1 改动文件清单

| 层 | 文件 | 类型 | 改动 |
| --- | --- | --- | --- |
| 客户端 | `client/src/types/question.ts` | 修改 | `Question` 新增 `reviewStage` / `nextReviewAt` / `lastReviewedAt` |
| 客户端 | `client/src/types/user.ts` | 修改 | `SyncItem` 新增同名字段（可选，兼容旧端） |
| 客户端 | `client/src/constants/index.ts` | 修改 | `SCHEMA_VERSION` 1→2；新增 `STORAGE_KEYS.reminderOn` |
| 客户端 | `client/src/utils/reviewSchedule.ts` | 新增 | 间隔表 + 纯函数（初始化 / 推进 / 到期判定 / 聚合摘要） |
| 客户端 | `client/src/services/questionService.ts` | 修改 | 入库初始化排期；`listDue` / `dueCount` / `markReviewed` / `backfillSchedule` |
| 客户端 | `client/src/services/syncService.ts` | 修改 | 排期字段上行/下行合并，远端缺字段时保留本地 |
| 客户端 | `client/src/services/reminderService.ts` | 新增 | 模板 ID 获取、`requestSubscribeMessage`、授权上报 |
| 客户端 | `client/src/utils/tabBadge.ts` | 新增 | 刷题 tab 角标写入/清除（两页复用） |
| 客户端 | `client/src/app.tsx` | 修改 | 启动时存量题目排期回填 |
| 客户端 | `client/src/pages/index/index.tsx` + `.module.scss` | 修改 | 品牌区精简、今日待复习双态卡片、入口文案、角标 |
| 客户端 | `client/src/pages/quiz/index.tsx` + `.module.scss` | 修改 | 到期队列、轮次标签、自评区、完成页三列统计、订阅引导、无到期空态 |
| 服务端 | `server/app/models/question_sync.py` | 修改 | 新增 3 个可空排期列 |
| 服务端 | `server/app/db/migrations.py` | 新增 | 幂等列迁移（`inspect` + `ALTER TABLE ADD COLUMN`） |
| 服务端 | `server/app/db/session.py` | 修改 | `init_db` 调用列迁移 + 导入新模型 |
| 服务端 | `server/app/models/reminder_subscription.py` | 新增 | 订阅状态/额度/最后发送时间 |
| 服务端 | `server/app/api/sync.py` | 修改 | 可选字段校验/序列化、按字段合并、内容安全送检条件收敛 |
| 服务端 | `server/app/api/reminder.py` | 新增 | `GET /reminder/config`、`POST /reminder/subscription` |
| 服务端 | `server/app/services/wechat_service.py` | 修改 | `get_access_token` 缓存 + `send_subscribe_message` |
| 服务端 | `server/app/services/reminder_scheduler.py` | 新增 | 每日扫描、聚合、静默/降频/额度/幂等 |
| 服务端 | `server/app/config.py` + `deploy/env.production.example` + `server/.env.example` | 修改 | 提醒开关、模板 ID、发送时刻、时区、额度上限 |
| 服务端 | `server/app/errors.py` | 修改 | 提醒域错误码 4001 / 4002 |
| 服务端 | `server/app/main.py` | 修改 | 挂载 reminder 路由 + 调度器生命周期 |
| 服务端 | `server/requirements.txt` | 修改 | 新增 `APScheduler` |
| 服务端 | `server/tests/test_sync_api.py`、`test_reminder_api.py`（新增）、`test_reminder_scheduler.py`（新增） | 修改/新增 | 契约与调度单测 |

### 1.2 受影响的现有行为

1. **刷题入口语义变更**：随机抽题下线，改为到期队列；未到期/无错题时进入空态。`questionService.pickRandom` / `resetRound` 保留但页面不再调用（删除由回归阶段决定）。
2. **同步写入频次变化**：复习自评会更新 `updatedAt` 触发同步；需同步收敛内容安全送检条件，避免每次自评重复送检。
3. **首页视觉变更**：移除「MVP 核心闭环」标签与副标语（主基线已确认）。
4. **数据库结构变化**：`question_sync` 增加 3 列、新增 `reminder_subscription` 表；本地已有 `server/app.db` 与生产 RDS 均需幂等迁移。

### 1.3 明确不改动

- 主 spec（`.trae/specs/mvp-reverse-docs/spec.md`）、主基线原型文件（已固化，不再改）
- 题库页 `pages/library`、我的页、录入页、识别/内容安全链路
- 登录、JWT、续期逻辑

---

## 二、风险清单与应对

| 编号 | 风险 | 影响 | 应对 |
| --- | --- | --- | --- |
| R1 | 现有库表无 Alembic，`create_all` 不会补列；生产 MySQL 与开发 SQLite 双环境 | 上线后同步接口 500 | 新增幂等列迁移：`inspect` 判列 → `ALTER TABLE ... ADD COLUMN`；重复启动不报错；用现有 `server/app.db` 实测 |
| R2 | 复习自评复用 `updatedAt` 触发同步，旧客户端会用旧 `updatedAt` 覆盖 | 排期被回滚 / 丢失 | 服务端仅在请求**显式携带**排期字段时覆盖；旧端缺失字段则保留库内值 |
| R3 | 内容安全送检按 `updatedAt` 判定，自评会放大送检量 | 配额消耗、复习卡顿 | 送检条件改为「content/answer 实际变化」；新增单测覆盖「仅排期变化不送检」 |
| R4 | 一次性订阅模板 ID / 字段未申请（个人主体） | 无法真机验收推送 | 配置项缺省即关闭调度；客户端模板 ID 为空时不弹授权、降级为站内提醒；模板字段映射集中在一处，拿到模板后只改映射 |
| R5 | 调度器多实例重复发送 | 用户收到多条 | 当前 uvicorn 单实例；发送前用 `last_sent_at` 条件更新做幂等，即使重复 tick 也只发一次 |
| R6 | 服务器时区非东八区 | 20:00 偏移、静默时段失效 | 调度统一用 `Asia/Shanghai`（可配 `REMINDER_TIMEZONE`），不依赖系统时区 |
| R7 | 存量题目无排期字段 | 首次上线无到期题 / 或集中爆发 | 启动时一次性回填：`reviewStage=1`、`nextReviewAt=次日 00:00`，不会出现「立即全量到期」 |
| R8 | 一次性订阅额度只减不增 | 提醒几天后失效 | 首页开关与完成页引导卡在每次复习结束后可再授权，`quota` 累加并设上限（默认 5） |
| R9 | 原生 tabBar 角标在 H5 预览不支持 | 开发期报错 | 角标工具函数 `try/catch` 包裹，失败静默 |

---

## 三、关键技术口径（编码前锁定）

### 3.1 数据字段

```ts
// Question / SyncItem 追加
reviewStage?: number          // 1..6 有效轮次；≥7 视为已掌握退出队列
nextReviewAt?: number | null  // 下次到期日 00:00（本地时区 ms）；已掌握为 null
lastReviewedAt?: number       // 最近一次复习时间戳
```

服务端 `question_sync` 对应列：`review_stage INT NULL`、`next_review_at BIGINT NULL`、`last_reviewed_at BIGINT NULL`。

### 3.2 算法口径

- 间隔表：`[1, 2, 4, 7, 15, 30]` 天；`MAX_STAGE = 6`。
- 入库：`reviewStage = 1`，`nextReviewAt = 次日 00:00`。
- 翻面即算完成；自评：
  - `记住了` → `reviewStage + 1`，下一间隔取 `INTERVALS[stage]` 天；`stage > 6` → `nextReviewAt = null`（已掌握）。
  - `没记住` → `reviewStage - 1`（最低 1），下一间隔取回退后轮次的天数。
- 到期判定：`nextReviewAt !== null && nextReviewAt <= endOfToday`（含逾期）。
- 队列排序：`nextReviewAt` 升序（逾期最久优先），同日按 `createdAt` 升序。
- 首页摘要：到期数、最早逾期天数、预计耗时（每题 30s）、涉及的轮次区间、下次到期日期与数量。

### 3.3 接口契约

| 方法 | 路径 | 鉴权 | 请求 | 响应 data |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/reminder/config` | 否 | - | `{ enabled, templateId, page, quietStart, quietEnd }` |
| POST | `/api/v1/reminder/subscription` | 是 | `{ accepted: number, enabled: boolean }` | `{ enabled, quota }` |

- 同步接口 `POST /sync/push`、`GET /sync/pull`：`items` 新增 3 个**可选**字段，其余不变。
- 新错误码：`4001` 提醒功能未配置 / 未开启，`4002` 提醒参数非法。

### 3.4 调度口径

- 每 5 分钟 tick；仅当东八区时间落在 `[20:00, 20:05)` 窗口执行。
- 21:00–08:00 静默（配置项，默认值与研讨一致）。
- 连续 3 天无 `lastReviewedAt` → 每周仅周一发送一次；恢复复习后立即回归每日。
- 每日每用户最多 1 条，多题聚合为一条，点击直达 `pages/quiz/index`。
- 无到期题、`enabled=false`、`quota<=0` 均不发送；发送失败只记日志，不重试（除 token 失效刷新一次）。

---

## 四、任务清单

> 勾选即代表该任务编码完成且自测通过；阶段 1/2/3/4 结束各暂停一次汇报。

### 阶段 1：客户端数据基座

- [x] **T01 类型与常量扩展**
  文件：`client/src/types/question.ts`、`client/src/types/user.ts`、`client/src/constants/index.ts`
  内容：`Question` / `SyncItem` 增加 3 个可选排期字段；`SCHEMA_VERSION = 2`；新增 `STORAGE_KEYS.reminderOn`
  验收：`npx tsc --noEmit` 通过；存量 Storage 数据读取不报错。

- [x] **T02 排期纯函数模块**
  文件：`client/src/utils/reviewSchedule.ts`（新增）
  内容：`REVIEW_INTERVALS_DAYS`、`MAX_STAGE`、`startOfDay/endOfDay`、`initSchedule`、`calcNextReview(stage, rating, now)`、`isDue`、`sortDue`、`dueSummary`、`nextDueInfo`
  验收：纯函数无副作用；`calcNextReview` 覆盖 记住了/没记住/已掌握 三条分支；类型完整无 `any`。

- [x] **T03 业务编排扩展**
  文件：`client/src/services/questionService.ts`、`client/src/app.tsx`
  内容：`create` 初始化排期；新增 `dueCount()` / `listDue()` / `markReviewed(id, rating)` / `backfillSchedule()`；`markReviewed` 同步 `lastReviewedAt`、`updatedAt` 并触发 `scheduleSync()`；App 启动执行一次回填
  验收：新建题次日到期；自评后轮次按口径推进；存量题回填后不生成立即到期。

- [x] **T04 同步协议传播排期**
  文件：`client/src/services/syncService.ts`
  内容：`questionToItem` 带上 3 字段；`mergeRemoteItems` 在远端提供字段时合并、缺失时保留本地；新增题按远端字段落库
  验收：登录态下复习一次 → 云端可见 `review_stage` / `next_review_at`；换设备拉取后轮次一致。

- [x] **T05 服务端表结构幂等迁移**
  文件：`server/app/models/question_sync.py`、`server/app/db/migrations.py`（新增）、`server/app/db/session.py`
  内容：新增 3 个可空列；`ensure_review_columns(engine)` 用 `inspect` 判列后 `ALTER TABLE`；`init_db` 调用
  验收：对现有 `server/app.db` 启动一次即补齐列；连续启动两次不报错；`PRAGMA table_info(question_sync)` 含三列。

### 阶段 2：服务端同步与触达

- [x] **S01 同步接口兼容与送检收敛**
  文件：`server/app/api/sync.py`、`server/tests/test_sync_api.py`
  内容：`_validate_item` 校验可选字段类型；`_serialize` 输出 3 字段；仅请求显式携带时覆盖；内容安全判定改为 content/answer 变化
  验收：新增单测覆盖「旧格式推送不清空排期」「排期字段往返一致」「仅排期变化不触发内容安全调用」，`pytest` 全绿。

- [x] **S02 配置与微信订阅能力**
  文件：`server/app/config.py`、`server/app/services/wechat_service.py`、`server/app/errors.py`、`server/.env.example`、`deploy/env.production.example`
  内容：`REMINDER_ENABLED` / `REMINDER_TEMPLATE_ID` / `REMINDER_HOUR` / `REMINDER_TIMEZONE` / `REMINDER_MAX_QUOTA` / 静默时段；`get_access_token`（进程内缓存 + 提前 60s 刷新）、`send_subscribe_message`；错误码 4001/4002
  验收：mock client 单测覆盖 token 缓存命中、token 失效重取一次、发送失败返回原因；未配置时 `enabled=false`。

- [x] **S03 订阅状态模型与接口**
  文件：`server/app/models/reminder_subscription.py`（新增）、`server/app/api/reminder.py`（新增）、`server/app/main.py`、`server/tests/test_reminder_api.py`（新增）
  内容：表 `reminder_subscription`（`user_id` 唯一、`enabled`、`quota`、`last_sent_at`、`updated_at`）；两个接口；路由挂载 `/api/v1`
  验收：未登录返回 2001；上报 `accepted=1` 后 `quota` 递增且不超上限；`enabled=false` 时 `quota` 归零；`config` 无鉴权可读。

- [x] **S04 每日提醒调度器**
  文件：`server/app/services/reminder_scheduler.py`（新增）、`server/app/main.py`、`server/requirements.txt`、`server/tests/test_reminder_scheduler.py`（新增）
  内容：APScheduler 每 5 分钟 tick；命中 20:00 窗口 → 汇总当日到期（`deleted=false AND next_review_at <= endOfToday`）→ 过滤静默/降频/额度 → 聚合发送 → 扣额度、写 `last_sent_at`
  验收：纯函数 `should_send` 单测覆盖静默时段、3 天降频、已发送幂等、额度为 0；同一窗口重复 tick 只发 1 条。

### 阶段 3：UI 还原（严格对齐主基线原型）

- [x] **U01 首页品牌区与今日待复习卡片**
  对齐节点：主基线 `错题本原型-01` 的 `.due-card`（`due-head` / `due-round` / `due-count` / `due-meta` / `due-actions` / `switch-line`）
  文件：`client/src/pages/index/index.tsx`、`index.module.scss`
  内容：删除 `MVP 核心闭环` 标签与副标语；新增双态卡片（待复习 / 今日已完成）；副入口 `开始刷题` → `开始复习`、`随机抽题` → `按到期顺序` 并换图标
  验收：到期数与摘要来自 `dueSummary`，非硬编码；卡片位于品牌区与「错题总数」之间；视觉与原型一致。

- [x] **U02 刷题 tab 角标与「稍后」**
  文件：`client/src/utils/tabBadge.ts`（新增）、`client/src/pages/index/index.tsx`、`client/src/pages/quiz/index.tsx`
  内容：`syncQuizBadge(count)` 写入/清除第 3 个 tab 角标（index=2）；首页 `useDidShow` 刷新；「稍后」仅当前停留隐藏卡片（不持久化）
  验收：待复习 8 道时角标为 8，清空后角标消失；H5 下无报错。

- [x] **U03 刷题页到期队列与自评**
  对齐节点：主基线 `错题本原型-03` 第 10/11 屏（`.progress-row` / `第 N 轮复习` chip / `.rate` 自评区）
  文件：`client/src/pages/quiz/index.tsx`、`index.module.scss`
  内容：`phase` 扩展为 `loading | card | emptyAll | emptyDue | done`；队列取 `listDue()`；进度 `1/8`；翻面后展示「没记住 / 记住了」；「本轮跳过」替代随机下一题
  验收：完成自评才进入下一题；自评结果落库并推进轮次；队列末题进入完成页。

- [x] **U04 完成页三列统计与订阅引导**
  对齐节点：主基线第 12 屏（`.done-sub` / `.stat-grid` 三列 / `.sub-card`）
  文件：`client/src/pages/quiz/index.tsx`、`index.module.scss`
  内容：副标题按到期数动态生成；统计改为「复习题数 / 记住了 / 待巩固」；新增订阅引导卡；移除「再来一轮」，仅保留「返回题库」
  验收：三项统计与本次自评一致；引导卡文案含 20:00 与明日到期数（可为 0 时给出兜底文案）。

- [x] **U05 无到期空态与样式收口**
  对齐节点：主基线第 13 屏（`empty-body` / `empty-title` / `empty-desc` / `empty-action`）
  文件：`client/src/pages/quiz/index.tsx`、`index.module.scss`
  内容：区分「一道错题都没有」与「今天没有到期题」两种空态；补齐 `.due-card` / `.rate` / `.sub-card` / `.stat-grid` / `.tab-badge` 等样式，复用现有变量
  验收：两种空态文案与跳转正确；`npx tsc --noEmit` 与样式构建通过。

### 阶段 4：订阅对接与真机联调

- [x] **I01 客户端提醒服务**
  文件：`client/src/services/reminderService.ts`（新增）、`client/src/constants/index.ts`
  内容：拉取 `/reminder/config`；`Taro.requestSubscribeMessage` 授权；统计 `accept` 数量并上报；本地 `u:reminderOn` 镜像开关；模板 ID 为空时不弹窗
  验收：拒绝授权不上报错误弹窗；已授权后开关状态与本地一致；接口失败降级为站内提醒。
  交付：2026-11-11 完成；模板未就绪/非微信端/授权失败统一降级站内提醒，同一 session 只弹一次。

- [x] **I02 开关与引导卡接线**
  文件：`client/src/pages/index/index.tsx`、`client/src/pages/quiz/index.tsx`
  内容：首页开关 → 授权/关闭上报；完成页引导卡按钮 → 同一授权流程；游客点击提示登录
  验收：游客不触发订阅弹窗；关闭后服务端 `enabled=false`；同一 session 内不重复弹窗。
  交付：2026-11-11 完成；首页游客弹登录引导，完成页游客 Toast 提示。

- [ ] **I03 真机联调**
  环境：微信开发者工具 + 真机（体验版）
  内容：录入新题 → 次日到期；复习自评 → 轮次推进；20:00 收到聚合消息 → 点击直达到期队列；连续 3 天未复习降频
  验收：全链路无阻断；消息文案与数量一致；异常（拒收/额度耗尽）不阻塞其他用户。
  状态：**待执行**，阻塞于一次性订阅模板 ID 与体验版上传；步骤清单见 `增量交付报告.md` 第六节。

### 阶段 5：回归与沉淀

- [x] **R01 回归 + ChangeLog + 交付报告**
  内容：`pytest` 全绿、`npx tsc --noEmit` 通过；录入/题库/识别/登录/同步回归；更新 `.trae/docs/change-log.md`；输出《增量交付报告》
  验收：存量功能无回归；change-log 记录编号、日期、摘要、影响模块、关联文档、是否待合并主 spec。
  交付：2026-11-11 完成；`pytest` 138 项通过、`tsc` 无新增错误、`build:weapp` 构建成功；存量页面手工走查并入 I03 真机联调。

---

## 五、里程碑与暂停点

| 里程碑 | 范围 | 暂停动作 |
| --- | --- | --- |
| M1 数据基座 | T01–T05、S01 | 汇报「字段/算法/迁移/同步兼容」自测结果 |
| M2 服务端触达 | S02–S04 | 汇报接口契约与调度单测结果 |
| M3 UI 还原 | U01–U05 | 汇报与主基线原型的对齐情况 |
| M4 联调与交付 | I01–I03、R01 | 输出交付报告与 change-log |

## 六、验证方案

- 服务端：`server/.venv/Scripts/python.exe -m pytest`（含同步兼容、订阅接口、调度纯函数）
- 客户端：`npx tsc --noEmit`；`npm run dev:weapp` 开发者工具走查
- 数据迁移：先用 `server/app.db` 副本验证补列，再走生产 RDS 预发
- 真机：订阅授权、20:00 推送、点击落地页、降频与额度耗尽

## 七、待确认项（附推荐默认）

1. **订阅模板**：已申请并通过，模板 ID `vxId8Kyj6pIlWCYJZik9sF65MmIMmzCQXGn0TULuaSw`；字段映射已对齐为 `thing1`（事项主题）/ `number16`（事项数目）/ `time23`（提醒时间）/ `thing12`（备注消息）。
2. **发送时刻**：固定 20:00，通过 `REMINDER_HOUR` 可配。推荐：默认 20:00 不做前台设置项。
3. **额度上限**：每次授权 +1，累计上限 5。推荐：上限 5，超出忽略。
4. **存量题回填**：统一「次日到期」。推荐：按次日 00:00，避免上线当天集中到期。
5. **「稍后」语义**：仅当前停留隐藏，不持久化。推荐：保持最简，不新增存储与视觉。

---

## 八、任务统计

- 总计：**18** 项（T01–T05 / S01–S04 / U01–U05 / I01–I03 / R01）
- 客户端数据与算法：5；服务端：4；UI：5；联调：3；回归：1
- 需用户确认后方可进入阶段五（编码）

