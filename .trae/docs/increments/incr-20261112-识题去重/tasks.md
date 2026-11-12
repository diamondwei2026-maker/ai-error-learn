# 开发任务清单 · 识题去重

- 增量编号：incr-20261112-识题去重
- 日期：2026-11-12
- 类型：普通轻量增量
- 依据：`方案.md`

---

## 阶段 1：数据基座

- [ ] **T01 类型与常量扩展**
  文件：`client/src/types/question.ts`、`client/src/types/user.ts`、`client/src/constants/index.ts`
  内容：`Question` / `SyncItem` 新增 `contentHash?: string`；`SCHEMA_VERSION` 2→3
  验收：`npx tsc --noEmit` 通过；存量 Storage 数据读取不报错

- [ ] **T02 哈希纯函数模块**
  文件：`client/src/utils/textHash.ts`（新增）
  内容：`normalizeForHash(text)` —— NFKC 全角转半角 → 空白合并 → 换行合并 → strip；`computeContentHash(text)` —— 调用 normalize 后 SHA-256，返回 64 字符 hex 字符串
  验收：纯函数无副作用；对相同输入始终返回相同哈希；无 `any` 类型

- [ ] **T03 服务端表结构幂等迁移**
  文件：`server/app/models/question_sync.py`、`server/app/db/migrations.py`、`server/app/db/session.py`
  内容：新增 `content_hash VARCHAR(64) NULL` 可空列 + `(user_id, content_hash)` 复合索引；`ensure_content_hash_column(engine)` 用 `inspect` 判列后 `ALTER TABLE`；`init_db` 调用
  验收：对现有 `server/app.db` 启动一次即补齐列；连续启动两次不报错

- [ ] **T04 业务编排扩展**
  文件：`client/src/services/questionService.ts`
  内容：`create()` 中对 `content` 计算 `contentHash` 并写入 `Question`；新增 `findDuplicates(contentHash: string): Question[]` —— 遍历本地列表，返回所有 `contentHash` 匹配的题目（排除自身）
  验收：新建题的 `contentHash` 正确；`findDuplicates` 能找到重复

- [ ] **T05 同步协议传播哈希**
  文件：`client/src/services/syncService.ts`、`server/app/api/sync.py`
  内容：上行/下行携带 `contentHash`；服务端允许该字段（兼容旧端缺失）；缺省保留已有值
  验收：登录态下新建带哈希的题 → 云端可见 `content_hash`；换设备拉取 → 哈希一致

## 阶段 2：存量回填

- [ ] **T06 存量题目批量回填哈希**
  文件：`client/src/app.tsx`
  内容：App 启动时遍历本地所有 Question，对缺失 `contentHash` 的题目计算并回填，调用 `storageRepo.saveQuestions` 持久化
  验收：启动后存量题目都有 `contentHash`；连续启动不重复计算

## 阶段 3：交互提醒

- [ ] **T07 重复提醒弹窗**
  文件：`client/src/components/ConfirmDialog/index.tsx`（扩展 或新建 `DuplicateWarning/index.tsx`）
  内容：三按钮弹窗 [查看已录入 / 仍然保存 / 取消]；展示已录入题目的题干预览 + 创建时间
  验收：样式与现有 `ConfirmDialog` 统一；三个按钮行为正确

- [ ] **T08 编辑页保存前检查**
  文件：`client/src/pages/edit/index.tsx`
  内容：保存前计算当前 content 的哈希 → 调 `questionService.findDuplicates` → 有命中则弹 T07 弹窗 → 三路分支；无命中直接保存
  验收：相同题干第二次保存弹提醒；不同题干不弹

## 阶段 4：回归与沉淀

- [ ] **R01 全链路回归**
  内容：`npx tsc --noEmit` + `npm run build:weapp`；服务端 `pytest` 全绿；手工走查：录入→保存→题库展示→同步→换设备拉取→去重提醒
  验收：存量功能无回归

- [ ] **R02 ChangeLog**
  文件：`.trae/docs/change-log.md`
  内容：追加变更记录（编号、日期、摘要、影响模块、关联文档、是否待合并主 spec）
