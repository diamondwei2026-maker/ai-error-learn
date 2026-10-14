# 增量任务拆分 · 用户系统

- 增量编号：incr-20261014-用户系统
- 关联：`./spec.md`（方案）、`./checklist.md`（验收）
- 说明：按「后端先行 → 前端基础 → 页面 → 集成 → 联调」顺序；每个任务标注**依赖**与**验证方式**。

---

## 阶段一：后端

### T1　后端数据库基础设施
- **内容**：SQLAlchemy 抽象层；engine/session/Base；`init_db()` 启动建表；`get_db` 依赖。
- **文件**：`server/app/db/__init__.py`、`db/base.py`、`db/session.py`
- **依赖**：无
- **验证**：`python -c "from app.db.session import init_db; init_db()"` 生成 `app.db`；`pytest` 不报导入错误。

### T2　后端用户模型与 JWT 鉴权
- **内容**：`User` ORM；`auth_service`（find_or_create_by_openid、签发/校验 access+refresh）；`deps/auth.get_current_user`。
- **文件**：`app/models/user.py`、`app/services/auth_service.py`、`app/deps/auth.py`
- **依赖**：T1
- **验证**：单测 `tests/test_auth_service.py`（签发→校验→过期→refresh）。

### T3　后端微信登录与 auth 接口
- **内容**：`wechat_service.code2session()`（httpx，错误码映射 2003/2004）；`POST /auth/login`、`POST /auth/refresh`。
- **文件**：`app/services/wechat_service.py`、`app/api/auth.py`、`app/models/schemas.py`（追加）
- **依赖**：T2
- **验证**：单测 `tests/test_auth_api.py`（mock code2session：成功 / 缺密钥 2003 / code 无效 2004 / refresh 失效 2002）。

### T4　后端 user 接口（含头像）
- **内容**：`GET /user/me`、`PATCH /user/me`、`POST /user/avatar`（multipart，≤2MB，存 `uploads/avatars/`）、`POST /user/delete`（删用户 + 其同步数据）。
- **文件**：`app/api/user.py`、`app/main.py`（静态目录挂载）、`app/config.py`（`AVATAR_MAX_BYTES`）
- **依赖**：T2
- **验证**：单测 `tests/test_user_api.py`（鉴权缺失 2001 / 改昵称 / 头像非图片 2006 / 注销后数据清空）。

### T5　后端 sync 接口
- **内容**：`POST /sync/push`（UPSERT + `updatedAt` 新者优先 + 墓碑删除）、`GET /sync/pull?since=`。
- **文件**：`app/models/question_sync.py`、`app/api/sync.py`
- **依赖**：T2
- **验证**：单测 `tests/test_sync_api.py`（插入 / 更新覆盖 / 旧数据不覆盖 / 删除墓碑 / 增量拉取 / 跨用户隔离 / 非法 3001）。

### T6　后端识别接口补鉴权
- **内容**：`/api/v1/recognize` 接入 `get_current_user`；受 `AUTH_REQUIRED` 开关控制。
- **文件**：`app/api/recognize.py`、`app/config.py`、`app/main.py`
- **依赖**：T2
- **验证**：单测——`AUTH_REQUIRED=true` 无 token 返回 401/2001；`false` 时行为与现状一致；现有 `tests/test_recognize_api.py` 不被破坏（必要时按开关调整）。

### T7　后端配置与依赖补齐
- **内容**：`config.py` 新增 8 项配置；`.env.example` 追加模板；`requirements.txt` 追加 SQLAlchemy / PyJWT。
- **文件**：`server/app/config.py`、`server/.env.example`、`server/requirements.txt`
- **依赖**：无
- **验证**：`tests/test_config.py` 扩展；`pip install -r requirements.txt` 成功。

---

## 阶段二：前端基础设施

### T8　常量与类型
- **内容**：`STORAGE_KEYS` 追加 `auth/removed/syncCursor`；用户域错误码文案；`AVATAR_MAX_BYTES`；`types/user.ts`。
- **文件**：`src/constants/index.ts`、`src/types/user.ts`
- **依赖**：无
- **验证**：`tsc` 无错；类型被后续模块正确引用。

### T9　authRepo（本地持久化）
- **内容**：`u:auth` 读写清；`q:removed` 墓碑读写；`q:syncCursor` 读写。
- **文件**：`src/services/repo/authRepo.ts`
- **依赖**：T8
- **验证**：手动 sanity（读写回环）；`tsc` 通过。

### T10　request 封装
- **内容**：统一 `request()`；baseURL 复用 `RECOGNIZE_API_BASE`；注入 `Authorization`；401/2002 自动 refresh 重试一次；错误码 → 文案。
- **文件**：`src/services/request.ts`
- **依赖**：T8、T9
- **验证**：联调（T15）验证；`tsc` 通过。

### T11　authService / userService / syncService
- **内容**：
  - `authService`：`login()`、`refresh()`、`logout()`、`restore()`
  - `userService`：`me()`、`updateNickname()`、`updateAvatar()`
  - `syncService`：`pushLocal()`、`pullRemote()`、`syncNow()`、`scheduleSync()`（节流 3s）+ 合并算法 + 墓碑处理
- **文件**：`src/services/authService.ts`、`userService.ts`、`syncService.ts`
- **依赖**：T9、T10
- **验证**：联调；合并算法用样例数据人工验证（本地较新 / 云端较新 / 墓碑）。

### T12　userStore
- **内容**：Zustand：`user`、`isLoggedIn`、`login/logout/refreshUser/updateProfile`。
- **文件**：`src/store/userStore.ts`
- **依赖**：T11
- **验证**：页面接入后状态切换正确。

---

## 阶段三：前端页面

### T13　「我的」页
- **内容**：未登录态（吉祥物头像 + 未登录 + 微信一键登录）；已登录态（头像昵称 + 点击进资料 + 退出/注销）；注销走 `ConfirmDialog`。
- **文件**：`src/pages/profile/index.tsx`、`index.config.ts`、`index.module.scss`
- **依赖**：T12
- **验证**：四态人工走查（未登录/已登录/退出确认/注销确认），视觉对齐视觉原型。

### T14　完善资料页
- **内容**：`chooseAvatar`（`Button open-type`）+ 昵称输入（`type="nickname"`，≤20 字）+ 底部保存；上传头像。
- **文件**：`src/pages/profile/edit/index.tsx`、`index.config.ts`、`index.module.scss`
- **依赖**：T12
- **验证**：改头像/昵称后返回「我的」即时生效；超长昵称被截断校验。

### T15　LoginSheet 组件 + 首页游客拦截
- **内容**：新增 `LoginSheet`（复用 ActionSheet 面板样式，不改 ActionSheet）；首页「拍照录入」入口校验登录态。
- **文件**：`src/components/LoginSheet/index.tsx`、`index.module.scss`、`src/pages/index/index.tsx`
- **依赖**：T12
- **验证**：游客点击弹层；「暂不登录」关闭后可继续刷题/进题库；已登录直接进采集流程。

### T16　tabBar 图标资源
- **内容**：新增 `profile.png` / `profile-selected.png`（81×81，线性人像，常规 `#4B5563` / 选中 `#056B36`），风格对齐现有 3 组图标。
- **文件**：`src/assets/tabbar/profile.png`、`profile-selected.png`
- **依赖**：无（可与页面并行）
- **验证**：微信开发者工具 tabBar 正常显示、选中态换色。

---

## 阶段四：集成

### T17　应用装配与既有模块接入
- **内容**：
  - `app.config.ts`：注册新页面 + tabBar 增「我的」
  - `app.tsx`：启动恢复登录态 + 已登录后台同步
  - `questionService`：`remove` 写墓碑；`create/remove` 触发 `scheduleSync`
  - `recognitionService`：请求头带 token
- **文件**：`src/app.config.ts`、`src/app.tsx`、`src/services/questionService.ts`、`src/services/recognitionService.ts`
- **依赖**：T11、T13–T16
- **验证**：`pnpm dev:weapp` 编译通过；四页 + 新页流转正常。

---

## 阶段五：联调与收尾

### T18　端到端联调
- **内容**：配 `server/.env`（`WECHAT_APP_SECRET`、`JWT_SECRET`）；模拟器真机登录、同步、退出、注销全链路。
- **依赖**：T7、T17
- **验证**：按 `checklist.md` 全项走查。

### T19　回归检查
- **内容**：既有 MVP 功能回归（录入识别、题库增删分页、刷题翻面、启动清理无主图片）。
- **依赖**：T18
- **验证**：`checklist.md` 回归项全绿；`pytest` 全通过。

### T20　文档归档
- **内容**：更新 `.trae/docs/change-log.md`（编号/日期/摘要/影响模块/文档路径/是否待合并主 spec）。
- **依赖**：T19
- **验证**：change-log 追加记录完整。

---

## 依赖关系速览

```
T1 → T2 → T3
        ├→ T4
        ├→ T5
        └→ T6
T7（独立）
T8 → T9 → T10 → T11 → T12
T12 → T13 / T14 / T15
T16（独立）
{T11,T13,T14,T15,T16} → T17 → T18 → T19 → T20
```

## 影响文件清单（汇总）

**后端新增**：`app/db/{__init__,base,session}.py`、`app/models/{user,question_sync}.py`、`app/deps/{__init__,auth}.py`、`app/services/{wechat_service,auth_service}.py`、`app/api/{auth,user,sync}.py`、`tests/{test_auth_service,test_auth_api,test_user_api,test_sync_api}.py`
**后端修改**：`app/config.py`、`app/main.py`、`app/api/recognize.py`、`app/models/schemas.py`、`.env.example`、`requirements.txt`、`tests/test_config.py`、`tests/test_recognize_api.py`
**前端新增**：`src/types/user.ts`、`src/services/{request,authService,userService,syncService}.ts`、`src/services/repo/authRepo.ts`、`src/store/userStore.ts`、`src/pages/profile/{index,index.config,index.module.scss}`、`src/pages/profile/edit/{index,index.config,index.module.scss}`、`src/components/LoginSheet/{index,index.module.scss}`、`src/assets/tabbar/{profile,profile-selected}.png`
**前端修改**：`src/app.config.ts`、`src/app.tsx`、`src/constants/index.ts`、`src/services/questionService.ts`、`src/services/recognitionService.ts`、`src/pages/index/index.tsx`
**文档**：`.trae/docs/change-log.md`
