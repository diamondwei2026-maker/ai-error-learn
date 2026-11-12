# 体验版「待复习」与「订阅消息」缺失修复计划

## 根因分析

经过代码走查，确认用户反馈的两个问题指向同一个根因链：

### 问题 1：首页没有看到待复习卡片

**根因：首页 `showDueCard` 条件过于严苛，导致提醒开关也被一并隐藏。**

```ts
// pages/index/index.tsx:155
const showDueCard = total > 0 && !snoozed && (due.count > 0 || reviewedToday > 0);
```

当用户的错题**都还没到期**（新录入 → 次日到期），且**今天还没复习过**时：
- `due.count = 0`，`reviewedToday = 0` → `showDueCard = false`
- 整个待复习卡片 + 里面的「每日 20:00 微信提醒」开关**都不渲染**
- 用户只看到错题总数卡片，完全看不到复习相关入口

### 问题 2：没有看到订阅消息授权弹窗

**根因 A（代码）：订阅开关嵌套在待复习卡片内，卡片被隐藏时开关自然也看不到。** 这是问题 1 的直接连锁反应。

**根因 B（配置，需确认）：** 线上服务器可能未配置 `REMINDER_ENABLED=true` 或 `REMINDER_TEMPLATE_ID`。若线上 `reminder_ready=false`，客户端 `GET /reminder/config` 返回 `enabled=false`，`reminderService.enable()` 会直接降级为「已开启站内提醒」，不走 `requestSubscribeMessage`。本地 `.env` 已正确配置，但线上服务器 `.env` 需部署时同步。

---

## 修复方案

### 改动 1：首页提醒开关独立区块（核心修复）

将「每日 20:00 微信提醒」开关从待复习卡片内**拆出**，变成独立区块，确保**有错题时始终可见**。

**改动文件：** `client/src/pages/index/index.tsx` + `index.module.scss`

**当前结构：**
```
showDueCard = true 时 → 渲染 dueCard（含 reminderSwitch）
showDueCard = false 时 → 什么都不渲染
```

**目标结构：**
```
有错题时（total > 0）→ 始终渲染提醒开关区块（独立于 dueCard）
待复习卡片 → 保持现有 showDueCard 条件（有待复习/已复习才显示）
```

提醒开关区块建议放在「错题总数」卡片下方，作为一个独立的轻量行（类似 iOS 设置中的开关行样式），包含：
- 铃铛图标 + 「每日 20:00 微信提醒」文字
- 开关控件
- 点击时保持现有 `toggleReminder` 逻辑不变

### 改动 2：线上服务器配置核查与部署

**检查清单：**
1. 线上服务器 `.env` 中 `REMINDER_ENABLED=true`
2. `REMINDER_TEMPLATE_ID=vxId8Kyj6pIlWCYJZik9sF65MmIMmzCQXGn0TULuaSw`
3. `WECHAT_APP_SECRET` 已配置
4. 重启服务让配置生效
5. 用 `curl https://你的API域名/api/v1/reminder/config` 验证返回 `enabled: true` 和正确的 `templateId`

### 改动 3（可选增强）：空态时显示下次到期预览

当 `showDueCard = false` 但有错题时，在独立的提醒开关区块上方增加一行轻量文案：
- 有排期但未到期：「下次到期：明天 / X 天后 · 共 N 道」（复用已有的 `nextDue` 状态）
- 无排期（不应该发生，`backfillSchedule` 会回填）：不显示

这样首页信息更完整，用户不会感觉「错题白录入了」。

---

## 具体改动步骤

### Step 1：首页结构拆分（前端）

文件：`client/src/pages/index/index.tsx`

1. 把 `reminderSwitch` 的 JSX 从 `dueCard` 内移到 `dueCard` 外部
2. 用 `total > 0` 作为独立开关区块的渲染条件
3. 可选：在开关区块上方加一行 `nextDueText` 轻量预览文案
4. 开关区块样式新增 `.reminderLine` class，独立于 `.dueCard`

### Step 2：样式补齐（前端）

文件：`client/src/pages/index/index.module.scss`

- 新增 `.reminderLine`（独立行，flex 布局，图标+文字+开关，与现有 `.switchLine` 视觉一致但更轻量，无边框背景）
- 确认 `.switchLine` 原有样式仍兼容 dueCard 内的使用

### Step 3：线上服务器配置核查

- SSH 到服务器检查 `.env` 三个关键变量
- 确认后 `systemctl restart error-learn-api`
- 用 curl 验证 `/api/v1/reminder/config` 返回值

### Step 4：重新构建 + 上传体验版

- `cd client && npm run build:weapp`
- 微信开发者工具 → 上传体验版

### Step 5：真机验证

- 新录入错题（未到期）→ 首页应显示：错题总数卡片 + 提醒开关
- 点击提醒开关 → 弹订阅消息授权面板
- 授权后 → Toast 提示成功
- 到期后（次日）→ 首页显示待复习卡片 + 数量正确

---

## 风险与注意事项

| 风险 | 处理 |
| --- | --- |
| 线上服务器未重启，`.env` 新值未生效 | 提醒用户需手动重启；用 curl 验证 |
| `prompted` 模块级变量导致 session 内二次点击不弹窗 | 已确认当前实现「同一 session 只弹一次」为设计意图，无需修改 |
| 真机测试需要等到次日才能看到到期卡片 | 可在代码中临时把 `REVIEW_INTERVALS_DAYS[0]` 从 1 改为 0.01（约 15 分钟后到期）快速验证，验证完改回 |
| H5 预览不支持开关组件的 toggle 动画 | 已有 try/catch 兜底，静默降级 |

## 验收标准

1. ✅ 有错题但未到期时，首页仍显示提醒开关
2. ✅ 点击开关弹出微信订阅消息授权面板
3. ✅ 授权后 Toast 提示「已开启，每天 20:00 提醒你」
4. ✅ 关闭后 Toast 提示「已关闭微信提醒」，开关状态正确回写
5. ✅ 到期后首页显示待复习卡片，数量正确
6. ✅ 关闭开关后不再弹授权（session 内）
7. ✅ `npx tsc --noEmit` 无新增错误
8. ✅ `npm run build:weapp` 构建成功
