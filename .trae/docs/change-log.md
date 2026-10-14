# 全局变更索引（change-log）

> 全局规则约束：每次增量开发完成，必须在此追加变更记录。
> 字段：**编号 / 日期 / 变更摘要 / 影响模块 / 关联文档路径 / 是否待合并主 spec**

---

## incr-20261014-用户系统

- **编号**：incr-20261014-用户系统
- **日期**：2026-10-14
- **变更摘要**：
  新增用户体系。包含：微信一键登录、退出登录、注销账号、「我的」Tab 页（tabBar 3→4 项）、完善资料（头像 chooseAvatar + 昵称）、登录后自动云端**文本**同步（用户无感知）、识别接口补鉴权、游客模式（仅「拍照识别」需登录）。
  后端新增 SQLAlchemy ORM 账号服务（开发期 SQLite，上线切阿里云 RDS）+ JWT 鉴权，新增 `auth` / `user` / `sync` 三类接口。
- **影响模块**：
  - 前端（`client/`）
    - 新增：`src/pages/profile/**`、`src/pages/profile/edit/**`、`src/components/LoginSheet/**`、`src/services/{request,authService,userService,syncService}.ts`、`src/services/repo/authRepo.ts`、`src/store/userStore.ts`、`src/types/user.ts`、`src/assets/tabbar/profile.png`、`profile-selected.png`
    - 修改：`src/app.config.ts`、`src/app.tsx`、`src/constants/index.ts`、`src/services/questionService.ts`、`src/services/recognitionService.ts`、`src/pages/index/index.tsx`
  - 后端（`server/`）
    - 新增：`app/db/**`、`app/models/user.py`、`app/models/question_sync.py`、`app/deps/**`、`app/services/auth_service.py`、`app/services/wechat_service.py`、`app/api/{auth,user,sync}.py`、`app/errors.py`、`app/utils/response.py`
    - 修改：`app/config.py`、`app/main.py`、`app/api/recognize.py`、`app/models/schemas.py`、`requirements.txt`、`.env.example`
    - 测试：新增 `tests/{conftest,test_auth_service,test_auth_api,test_user_api,test_sync_api,test_recognize_auth}.py`；扩展 `tests/test_config.py`
  - 其它：`.gitignore`（新增运行期产物忽略）
- **关联文档路径**：`.trae/docs/increments/incr-20261014-用户系统/`
  - `研讨记录.md`、`spec.md`、`tasks.md`、`checklist.md`
  - `prototype/skeleton/用户系统原型-骨架.html`、`prototype/visual/用户系统原型-视觉.html`
- **是否待合并主 spec**：**否**（高风险增量独立归档，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 后端：`.venv\Scripts\python.exe -m pytest` → **80 passed**
  - 前端：`tsc --noEmit` 无新增类型错误（仅全仓既有的 `React` 未使用告警）；`npm run build:weapp` → **构建成功**
- **上线前置条件（不阻塞开发）**：
  1. 配置 `server/.env` 的 `WECHAT_APP_SECRET` 与 `JWT_SECRET`
  2. 小程序后台配置《用户隐私保护指引》，声明「头像昵称」「登录」
  3. 真机联调需后端具备 HTTPS 合法域名（备案）
- **回滚方式**：识别接口鉴权可置 `AUTH_REQUIRED=false` 恢复旧行为；前端 tabBar/页面为纯追加，回退 `app.config.ts` 即恢复
