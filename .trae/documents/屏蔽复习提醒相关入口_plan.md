# 屏蔽复习提醒相关入口（当前阶段不做学习提醒）

- 日期：2026-11-12
- 目标：当前阶段不进行任何学习提醒。屏蔽微信订阅提醒入口与站内待复习提醒（首页待复习卡片、刷题 tab 角标），并同步关闭服务端定时推送。
- 原则：集中开关、保留既有代码与接口，后续改一处开关即可恢复；符合项目「兼容层优先、支持回滚」规范。

## 一、现状分析

复习提醒由 `incr-20261111-复习提醒` 引入，当前用户可见入口与服务端触达点如下：

| 位置 | 内容 | 文件 |
| --- | --- | --- |
| 首页 | 「今日待复习 / 今日已完成」双态卡片 + 「每日 20:00 微信提醒」开关 | [index.tsx](file:///d:/Users/weij/ai-error-learn/client/src/pages/index/index.tsx#L155-L227) |
| 刷题完成页 | 「别错过下次复习」引导卡 + 「开启微信提醒」按钮 | [quiz/index.tsx](file:///d:/Users/weij/ai-error-learn/client/src/pages/quiz/index.tsx#L218-L234) |
| 刷题 tab | 待复习数量角标 | [tabBadge.ts](file:///d:/Users/weij/ai-error-learn/client/src/utils/tabBadge.ts) |
| 服务端 | 每日 20:00 APScheduler 推送、`/reminder/config` 返回 `enabled` | [reminder_scheduler.py](file:///d:/Users/weij/ai-error-learn/server/app/services/reminder_scheduler.py#L146-L171)、[reminder.py](file:///d:/Users/weij/ai-error-learn/server/app/api/reminder.py#L33-L45) |
| 配置 | 本地 `server/.env` 为 `REMINDER_ENABLED=true`；生产模板同为 `true` | [.env](file:///d:/Users/weij/ai-error-learn/server/.env#L39)、[env.production.example](file:///d:/Users/weij/ai-error-learn/deploy/env.production.example#L69-L71) |

已确认事实：

- `ReminderScheduler.start()` 与 `run_tick()` 都以 `settings.reminder_ready` 为前置条件；`reminder_ready = reminder_enabled && reminder_template_id && wechat_configured`（[config.py](file:///d:/Users/weij/ai-error-learn/server/app/config.py#L112-L116)）。因此把 `REMINDER_ENABLED` 置 false 即可同时停推送、停接口下发模板。
- `GET /reminder/config` 在未就绪时返回 `enabled=false`，客户端不会再弹订阅面板。
- 前端提醒入口只有首页与刷题完成页两处；`reminderService` 仅被这两个页面引用。
- 复习排期、到期队列、刷题流程与提醒入口相互独立，屏蔽提醒不影响复习功能本身。

## 二、方案总览

1. 客户端新增集中开关常量 `REVIEW_REMINDER_ENABLED = false`，用条件渲染屏蔽：
   - 首页「今日待复习 / 今日已完成」卡片（卡片内含微信提醒开关）；
   - 刷题完成页「别错过下次复习」订阅引导卡；
   - 刷题 tab 待复习角标（开关关闭时主动清除历史角标）。
2. 服务端通过配置关闭：`server/.env` 与生产环境模板的 `REMINDER_ENABLED` 置 `false`，调度器不启动、接口返回未开启。
3. 保留 `reminderService`、`/reminder/*` 接口、调度器、数据表与单测，不做删除；恢复时只需把前端常量改回 `true` 并将 `REMINDER_ENABLED` 置 `true`。
4. 本次为入口屏蔽（删减展示），无新增/改版视觉稿，不进入双阶段原型流程。

## 三、详细改动

### 1. `client/src/constants/index.ts`

新增集中开关（放在 `PAGE_SIZE` 之后）：

```ts
/**
 * 学习提醒（复习提醒）总开关。
 * 当前阶段关闭：隐藏首页待复习卡片、刷题 tab 角标与微信订阅提醒入口；
 * 复习排期与刷题流程不受影响。恢复时改为 true。
 */
export const REVIEW_REMINDER_ENABLED = false;
```

### 2. `client/src/utils/tabBadge.ts`

在 `syncQuizBadge` 内统一收敛角标：开关关闭时目标数量恒为 0（清除可能残留的角标），不新增调用点改动。

```ts
import { REVIEW_REMINDER_ENABLED } from '@/constants'
...
export function syncQuizBadge(count: number): void {
  if (!isWeapp) return
  const next = REVIEW_REMINDER_ENABLED ? count : 0
  try {
    if (next > 0) {
      Taro.setTabBarBadge({ index: QUIZ_TAB_INDEX, text: next > 99 ? '99+' : String(next) }).catch(() => undefined)
      return
    }
    Taro.removeTabBarBadge({ index: QUIZ_TAB_INDEX }).catch(() => undefined)
  } catch (error) {
    console.warn('[tabBadge] sync failed', error)
  }
}
```

说明：该函数是唯一的角标写入口，集中处理可覆盖首页/刷题的 7 处调用，避免逐点改动。

### 3. `client/src/pages/index/index.tsx`

- 引入 `REVIEW_REMINDER_ENABLED`。
- 修改 `showDueCard`：

```ts
const showDueCard =
  REVIEW_REMINDER_ENABLED && total > 0 && !snoozed && (due.count > 0 || reviewedToday > 0);
```

效果：整个待复习卡片（含「每日 20:00 微信提醒」开关、开始复习/稍后按钮）不再渲染；`refreshReview`、`reminderSwitch`、`toggleReminder` 等代码保留，开关打开即恢复。
保留不动：首页底部「开始复习」次级入口（属于复习功能入口，非提醒）。

### 4. `client/src/pages/quiz/index.tsx`

- 引入 `REVIEW_REMINDER_ENABLED`。
- 完成页订阅引导卡改为条件渲染：

```tsx
{REVIEW_REMINDER_ENABLED ? (
  <View className={styles.subCard}>
    {/* 原「别错过下次复习」引导卡内容保持不变 */}
  </View>
) : null}
```

保留不动：`reminderOn` 状态、`handleSubscribe`、`useDidShow` 中的本地镜像读取、到期空态「下次到期」提示（属于复习流程信息，不是提醒入口）。

### 5. `server/.env`

第 39 行 `REMINDER_ENABLED=true` → `false`（补一行中文注释：当前阶段关闭学习提醒）。

### 6. `deploy/env.production.example`

复习提醒段 `REMINDER_ENABLED=true` → `false`，注释注明「当前阶段关闭（不做学习提醒），恢复时改回 true」。`server/.env.example` 保持 false 不变。

### 7. 文档与记录

- 在 `.trae/docs/change-log.md` 末尾追加记录：
  - 编号：`fix-20261112-屏蔽复习提醒入口`
  - 变更摘要：新增客户端集中开关 `REVIEW_REMINDER_ENABLED=false`，屏蔽首页待复习卡片、tab 角标与完成页订阅引导；服务端 `REMINDER_ENABLED=false` 停止定时推送；代码与接口保留可恢复。
  - 影响模块：`client/src/constants/index.ts`、`client/src/utils/tabBadge.ts`、`client/src/pages/index/index.tsx`、`client/src/pages/quiz/index.tsx`、`server/.env`、`deploy/env.production.example`
  - 关联文档：本 plan 文件；是否待合并主 spec：否
- 按会话规则新建进度清单 `.trae/todolist/屏蔽复习提醒相关入口.md`（记录任务总数、已完成/未完成项）。

## 四、假设与决策

- 「屏蔽复习提醒入口」按已确认口径执行：仅微信订阅提醒 + 站内提醒（待复习卡片、tab 角标），不隐藏「开始复习」与刷题流程。
- 采用集中开关而非删除代码，保留后续恢复能力。
- 服务端同步关闭推送（`REMINDER_ENABLED=false`），不改调度器/接口/表结构代码，避免影响既有单测与数据。
- 不清理 `reminder_subscription` 表内历史数据：调度器不启动即不会发送，后续恢复可直接复用。
- 不制作新原型：本次仅做现存模块的显隐删减，无视觉改版。

## 五、验证步骤

1. `cd client && npx tsc --noEmit`：无新增类型错误。
2. `cd client && npm run build:weapp`：构建通过。
3. 微信开发者工具/H5 走查：
   - 首页不出现「今日待复习 / 今日已完成」卡片与微信提醒开关；
   - 刷题完成页不出现「别错过下次复习 / 开启微信提醒」；
   - 刷题 tab 无角标（历史角标被清除）；
   - 「开始复习」与刷题、翻面、自评流程正常。
4. 服务端：重启后日志出现「复习提醒未配置（开关/模板 ID/微信密钥），调度器不启动」；`GET /api/v1/reminder/config` 返回 `enabled=false`（本地无 token 场景可只验证日志）。
5. `cd server && .venv/Scripts/python.exe -m pytest -q`：提醒相关单测仍全通过（未改服务端代码，作回归确认）。

## 六、回滚方式

- 前端：将 `REVIEW_REMINDER_ENABLED` 改回 `true` 并重新构建，所有入口按原逻辑恢复。
- 服务端：`server/.env` 与生产 `.env` 的 `REMINDER_ENABLED` 改回 `true` 并重启 `error-learn-api`。
- 无需回滚数据库结构与接口代码。
