# 增量任务拆分 · 首次登录引导完善资料

- 增量编号：incr-20261014-首次登录资料引导
- 关联：`./方案.md`（方案）、`./checklist.md`（验收）
- 说明：本增量**仅前端、仅行为**，无后端改动、无视觉改动。

---

### T1　常量与本地持久化
- **内容**：`STORAGE_KEYS` 追加 `nickPrompted`；`authRepo` 新增 `isNicknamePrompted()` / `markNicknamePrompted()`；`clearAll()` 移除该键。
- **文件**：`src/constants/index.ts`、`src/services/repo/authRepo.ts`
- **依赖**：无
- **验证**：`tsc` 通过；注销后标志被清除。

### T2　userStore 引导判定
- **内容**：`login()` 返回 `UserProfile`；新增 `shouldGuideProfileSetup()`（`已登录 && 昵称为空 && 未引导过`）与 `markProfileSetupGuided()`。
- **文件**：`src/store/userStore.ts`
- **依赖**：T1
- **验证**：`tsc` 通过；两处登录后状态正确。

### T3　登录调用点接入引导
- **内容**：`pages/index`、`pages/profile` 登录成功后，若需引导 → 标记并 `navigateTo('/pages/profile/edit/index')`。
- **文件**：`src/pages/index/index.tsx`、`src/pages/profile/index.tsx`
- **依赖**：T2
- **验证**：首次登录自动进入完善资料；再次登录不进入。

### T4　验证与文档
- **内容**：`tsc --noEmit`、`npm run build:weapp`、后端 `pytest` 回归；更新 `change-log.md` 与 `checklist.md`。
- **依赖**：T3
- **验证**：构建成功、pytest 全绿、change-log 记录完整。
