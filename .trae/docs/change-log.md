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

---

## incr-20261014-首次登录资料引导

- **编号**：incr-20261014-首次登录资料引导
- **日期**：2026-10-14
- **变更摘要**：
  首次登录后引导完善资料。用户主动完成「微信一键登录」后，若昵称为空且从未引导过，**自动进入现有「完善资料」页**，由其主动选择头像（`chooseAvatar`）并填写昵称（`input type="nickname"`）；点顶部返回即跳过。仅首次引导一次（本地标志 `u:nickPrompted`，注销时清除）。
  **无界面视觉改动**（不新增按钮/文案，页面沿用现状）；**无后端改动**。
- **影响模块**：
  - 前端（`client/`）
    - 修改：`src/constants/index.ts`（新增 `STORAGE_KEYS.nickPrompted`）、`src/services/repo/authRepo.ts`（`isNicknamePrompted` / `markNicknamePrompted`，`clearAll` 清理该键）、`src/store/userStore.ts`（`login()` 返回 `UserProfile`；新增 `shouldGuideProfileSetup` / `markProfileSetupGuided`）、`src/pages/index/index.tsx`、`src/pages/profile/index.tsx`（登录成功后按需跳转「完善资料」）
- **关联文档路径**：`.trae/docs/increments/incr-20261014-首次登录资料引导/`
  - `方案.md`、`tasks.md`、`checklist.md`、`prototype/skeleton/首次登录引导原型-骨架.html`
- **是否待合并主 spec**：**否**（普通轻量增量，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 前端：`tsc --noEmit` 无新增类型错误（仅全仓既有的 `React` 未使用告警）；`npm run build:weapp` → **构建成功**（30.34s）
  - 后端：`.venv\Scripts\python.exe -m pytest` → **80 passed**（未改后端，无回归）
- **回滚方式**：移除两处登录成功后的跳转调用即可恢复；本地标志 `u:nickPrompted` 为独立键，不影响既有数据

---

## ops-20261014-部署上线方案

- **编号**：ops-20261014-部署上线方案
- **日期**：2026-10-14
- **变更摘要**：
  输出正式上线方案与配套部署产物，目标环境为**阿里云 ECS 自建 + 云 RDS MySQL + 已备案域名 HTTPS**。
  前端消除硬编码局域网 IP，后端地址改为构建期环境变量 `TARO_APP_API_BASE` 注入（`.env.development` / `.env.production` 分环境）；
  后端新增 MySQL 驱动 PyMySQL 以支持 RDS 连接串切换；新增 `deploy/` 部署产物（Nginx 反代、systemd 守护、生产环境变量模板、一键部署脚本、部署指南）。
  **无业务逻辑改动、无 UI 改动、无新增功能。**
- **影响模块**：
  - 前端（`client/`）
    - 新增：`.env.development`、`.env.production`
    - 修改：`src/constants/index.ts`（`API_BASE` 改由 `process.env.TARO_APP_API_BASE` 注入，`RECOGNIZE_API_BASE` 保留旧别名）、`types/global.d.ts`（新增 `TARO_APP_API_BASE` 类型声明）
  - 后端（`server/`）
    - 修改：`requirements.txt`（新增 `PyMySQL>=1.1,<2.0`）
  - 部署产物（新增 `deploy/`）
    - `nginx/error-learn.conf`、`systemd/error-learn-api.service`、`env.production.example`、`deploy.sh`、`README.md`（`README.md` 已于 2026-10-15 合并进部署教程后删除）
- **关联文档路径**：`.trae/documents/部署教程.md`（原 `部署上线方案.md` 已于 2026-10-15 合并重写，见下条）
- **是否待合并主 spec**：**否**（运维/上线准备，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 后端：`.venv\Scripts\python.exe -m pytest` → **80 passed**（无回归）
  - 前端：`npm run build:weapp` → **构建成功**
- **上线前置条件（待用户提供，不阻塞产物落地）**：
  1. 正式已备案域名（替换 `.env.production` 与 Nginx/systemd 中的占位）
  2. RDS 连接信息（内网地址 / 账号 / 密码）与 ECS 内网 IP 白名单
  3. 微信 `WECHAT_APP_SECRET`、`JWT_SECRET`、视觉模型 `VISION_API_KEY`、SSL 证书
  4. 微信公众平台配置 request / uploadFile / downloadFile 合法域名 + 《用户隐私保护指引》
- **回滚方式**：代码回退 `git checkout <上一可用提交>` 后重启 service；前端在微信后台「版本回退」；配置回退 `server/.env.bak`；识别接口鉴权应急开关 `AUTH_REQUIRED=false`

---

## docs-20261015-部署文档精简

- **编号**：docs-20261015-部署文档精简
- **日期**：2026-10-15
- **变更摘要**：
  将部署文档由「方案长文 + 步骤 README」两份合并为**一份纯操作教程** `.trae/documents/部署教程.md`，删除现状分析、改动清单、风险表、交付物清单、物料速览等非教程内容。
  **新增与现有环境共存章节**：服务器上已有 Nginx 占用 80/443 时，复用现有 Nginx、新增独立 `server_name` 子域名接入，命令只 `reload` 不 `restart`，并含端口冲突、运行用户（www-data/nginx）、`caching_sha2_password` 依赖等对症处理。
  **无代码改动、无配置行为改动。**
- **影响模块**：
  - 文档：新增 `.trae/documents/部署教程.md`（唯一部署文档）
  - 删除：`.trae/documents/部署上线方案.md`、`deploy/README.md`、`.trae/documents/部署方案物料获取指南-更新计划.md`（均已合并进新教程）
  - 注释：`deploy/deploy.sh`（头部前置说明的文档引用改指新教程）
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档整理，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：教程命令与仓库实际逐条比对一致（`/api/v1/health`、`npm run build:weapp`、`deploy.sh`、systemd `<DEPLOY_DIR>` 占位、nginx 三处占位、`env.production.example` 键名、AppID `wx683110d829c1f0f9`、`UPLOADS_DIR` 与 `/static/` alias 对应）；全仓检索确认无失效文档引用
- **回滚方式**：`git checkout <上一可用提交>` 恢复被删的两份文档与 `deploy.sh` 注释

---

## docs-20261015-部署教程联网校对

- **编号**：docs-20261015-部署教程联网校对
- **日期**：2026-10-15
- **变更摘要**：
  按 2026-10 现行官方规则对 `.trae/documents/部署教程.md` 做联网校对，修订 8 处：
  ① 补「前置三件事」——域名 ICP 备案、**小程序备案**（2023-09-04 起未备案不可上架）、ECS 与 RDS 同地域同 VPC；
  ② 证书策略换挡——阿里云免费 DV（现名「个人测试证书」）**90 天且不支持自动续期**，新增 **acme.sh + DNS-01 自动续签**为推荐方案（DNS 验证不占 80 端口，绕开现有站点占用的 80），控制台免费证书降为备选、复用通配符证书为第三方案；
  ③ nginx HTTP/2 写法改为**版本分支**（≥1.25.1 用 `http2 on;`；Ubuntu 24.04 apt 版 1.24.0 必须用 `listen 443 ssl http2;`）+ 证书替换后必须 reload；
  ④ 装依赖补 `pip install "PyMySQL[rsa]"`（MySQL 8 的 `caching_sha2_password` 需 cryptography，8.4 已移除 `mysql_native_password`）；
  ⑤ 排障按阿里云官方错误码重写（2003 / 1045#28000 / 1045 Access denied / 2059 / 2006）；
  ⑥ 微信侧隐私指引入口更正为「设置 → 功能设置 → 用户隐私保护指引」并补「配置后需重新审核发布才生效」；
  ⑦ 补微信侧域名硬性要求（须已备案、不能带端口、不可配置 `api.weixin.qq.com`、TLS ≥ 1.2 + ECDHE）；
  ⑧ 新增「参考来源」附录（8 条官方来源 + 校对日期）。
  **无代码改动、无配置行为改动。**
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：8 处改动逐条比对官方来源；nginx 版本分支、acme.sh 五步、openssl 校验命令均可直接执行且不影响现有站点；与仓库事实（`/api/v1/health`、`npm run build:weapp`、AppID `wx683110d829c1f0f9`、`env.production.example` 键名、`deploy.sh`）一致性复核通过
- **回滚方式**：`git checkout <上一可用提交>` 还原教程

---

## incr-20261015-上线合规改造

- **编号**：incr-20261015-上线合规改造
- **日期**：2026-10-15
- **变更摘要**：
  微信小程序上线合规改造，落地 C1 + C2 两项阻塞项：
  ① **隐私授权接入**（C1/M1）——新增隐私弹层 + 授权编排，策略为「启动非阻断 + 被动兜底 + 主动前置」：启动查询授权状态后弹出弹层（用户可「暂不授权」，首页/题库/刷题照常可用）；任意隐私接口被拦截时弹同一弹层并在同意/拒绝后 `resolve`；昵称输入聚焦主动前置授权（`<input type="nickname">` 不触发被动监听，会静默降级）。
  ② **隐私政策 / 用户协议**（C2/M2）——新增 `pages/agreement` 页面（query `type=privacy|terms` 区分），「我的」页新增「服务协议」区块（未登录也显示），弹层内提供协议入口与「查看平台隐私协议」。
  **后端零改动**；不改动业务逻辑、数据模型、识别与同步链路、UI 设计语言。
- **影响模块**：
  - 前端（`client/`）
    - 新增：`src/store/privacyStore.ts`、`src/services/privacyService.ts`、`src/components/PrivacySheet/{index.tsx,index.module.scss}`、`src/pages/agreement/{index.tsx,index.module.scss,index.config.ts}`
    - 修改：`src/app.tsx`（启动注册监听 + 查询授权）、`src/app.config.ts`（注册协议页）、`src/constants/index.ts`（`AGREEMENT_TYPE`/`AGREEMENT_PAGE_PATH`/`AGREEMENT_TITLES`/`PRIVACY_DENIED_MESSAGE`）、`src/components/AppButton/index.tsx`（新增可选 `openType` + `onAgreePrivacyAuthorization`）、`src/services/captureService.ts`（拍照/相册前置授权守卫 + 拒绝提示）、`src/pages/index/index.tsx`、`src/pages/library/index.tsx`、`src/pages/quiz/index.tsx`（3 个 return 分支）、`src/pages/edit/index.tsx`（2 个 return 分支）、`src/pages/profile/index.tsx`（挂载 + 服务协议区块 + `.sectionLabel` 样式）、`src/pages/profile/edit/index.tsx`（挂载 + 昵称 `onFocus` 前置授权）
    - **挂载点合计 10 处**（6 页面 / 9 个 return 分支 + 协议页不挂载）
  - 后端（`server/`）：**无改动**
  - 文档：新增 `.trae/documents/上线合规代码改造方案.md`（上游方案，本次改造依据）
- **关联文档路径**：`.trae/docs/increments/incr-20261015-上线合规改造/`
  - `研讨记录.md`、`开发计划.md`
  - `prototype/skeleton/上线合规原型-骨架.html`、`prototype/visual/上线合规原型-视觉.html`
- **是否待合并主 spec**：**否**（普通增量走 `/plan`，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 前端：`tsc --noEmit` 无新增类型错误（仅全仓既有的 `React` 未使用基线告警）；`npm run build:weapp` → **构建成功**（56.13s）；产物含 `dist/pages/agreement/**`，`app.json` 已注册
  - 后端：`.venv\Scripts\python.exe -m pytest` → **80 passed**（未改后端，无回归）
  - ⚠️ 说明：直接运行 pytest 会因 `server/.env` 的 `DATABASE_URL` 仅填主机名（非合法连接串）而在 `create_app` 处报错（既有环境问题，非本次引入）；本次以「绕过 dotenv 装载」的方式完成回归验证
- **上线前置条件（不阻塞编码，阻塞上线）**：
  1. MP 后台配置《用户隐私保护指引》，声明：头像、昵称、微信登录标识、相机/相册（否则 `errno 112` / `appid privacy api banned`）
  2. 协议正文终审（尤其「第三方多模态大模型处理」披露与联系方式），须与后台指引口径一致
  3. 真机验证需后端 HTTPS 备案域名
- **回滚方式**：移除 10 处 `<PrivacySheet />` 与 `app.tsx` 的 `privacyService` 调用即恢复原状（微信自动回退官方隐私弹窗）；协议页为纯新增，删除页面 + `app.config.ts` 注册项 + 「我的」页区块即可；后端与数据无改动，无需回滚

