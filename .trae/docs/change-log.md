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

---

## ops-20261015-部署产物恢复

- **编号**：ops-20261015-部署产物恢复
- **日期**：2026-10-15
- **背景**：`ops-20261014-部署上线方案` / `docs-20261015-部署文档精简` / `docs-20261015-部署教程联网校对` 三条记录所描述的部署产物与教程，**从未提交入库**（`git log` 全 17 次提交均无相关路径），当前工作区亦不存在。本次按记录重建，使其可入库、可复用。
- **变更摘要**：
  重建部署产物与唯一部署教程，并补齐两处使其真正可跑的前置改动。
  **无业务逻辑改动、无 UI 改动、无新增功能。**
- **影响模块**：
  - 部署产物（重建 `deploy/`）
    - `deploy/nginx/error-learn.conf`（反代 `/api/`、静态 `/static/` alias、3 处占位、HTTP/2 版本分支注释）
    - `deploy/systemd/error-learn-api.service`（`<DEPLOY_DIR>` 占位、用户可替换）
    - `deploy/env.production.example`（生产变量模板，含 RDS 连接串与 `UPLOADS_DIR`）
    - `deploy/deploy.sh`（一键部署脚本，头部引用 `.trae/documents/部署教程.md`）
  - 前端（`client/`）
    - 新增：`.env.development`（局域网 IP）、`.env.production`（`TARO_APP_API_BASE=https://api.example.com`）
  - 后端（`server/`）
    - 修改：`requirements.txt`（新增 `PyMySQL>=1.1,<2.0`，支撑 RDS 连接串）
  - 文档：新增 `.trae/documents/部署教程.md`（纯操作教程：前置三件事 / 后端 / Nginx+HTTPS / 前端发布 / 微信侧配置 / 运维 / 排障 / 参考来源）
- **关联文档路径**：`.trae/documents/部署教程.md`；产物位于 `deploy/**`
- **是否待合并主 spec**：**否**（运维/上线准备，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：产物字段与仓库代码逐条比对一致（`/api/v1/health`、`/static` ↔ `UPLOADS_DIR`、`npm run build:weapp`、AppID `wx683110d829c1f0f9`、`client/src/constants/index.ts` 的 `TARO_APP_API_BASE`、`config.py` 键名、`requirements.txt`）；`deploy.sh` 的 sed 替换与 systemd/nginx 占位一一对应
- **待办（不阻塞产物，阻塞上线）**：① 替换 nginx/systemd/env 中的域名与证书占位；② 提交 `deploy/**`、`client/.env.production`、`client/.env.development` 入库
- **回滚方式**：删除 `deploy/`、两个 `.env` 文件与 `.trae/documents/部署教程.md`，并还原 `server/requirements.txt` 的 PyMySQL 行

---

## docs-20261015-部署教程共享ECS改写

- **编号**：docs-20261015-部署教程共享ECS改写
- **日期**：2026-10-15
- **背景**：用户实际环境为「ECS 已有原生 Nginx 站点（80/443 被占）+ 独立 RDS 实例 + 有备案主域名需新开子域名」。原教程以"全新服务器"为口径，把共存场景压缩为 §3.3 五条脚注，不匹配实际。本次以用户真实环境为主线重写教程，并最小化改造部署脚本以支持共享服务器。
- **变更摘要**：
  教程由"全新服务器口径"改写为"共享 ECS 共存主线"：新增「场景与前提」「现状勘察」「接入现有 Nginx」「影响范围与回滚」等章节；证书方案由三选一收敛为**只主推 DNS-01**（因 80 被既有站点占用，HTTP-01 不可用）；明确"不重装 Nginx、不改既有配置、只 reload 不 restart"。
  脚本 `deploy/deploy.sh` 增加 `PORT` 可配置与端口占用预检，并把端口注入 systemd 与 Nginx 配置。
  **无业务逻辑改动、无 UI 改动、无新增功能。**
- **影响模块**：
  - 文档：`.trae/documents/部署教程.md`（**重写**，11 章 + 参考来源）
  - 部署产物：`deploy/deploy.sh`（修改：新增 `PORT` 变量、端口占用预检 `ss -lnt`、systemd `--port` 与 nginx `127.0.0.1:8000` 端口替换、健康检查端口、用法注释）
  - 未改动：`deploy/nginx/error-learn.conf`、`deploy/systemd/error-learn-api.service`、`deploy/env.production.example`、前端代码、后端代码
- **关联文档路径**：`.trae/documents/部署教程.md`；方案 `.trae/documents/更新部署教程-阿里云共享ECS场景.md`
- **是否待合并主 spec**：**否**（文档 + 部署脚本，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - `bash -n deploy/deploy.sh` → **exit 0**（语法通过，Git Bash）
  - 脚本全文核对：仅 `systemctl reload nginx`（无 `nginx restart`）、无修改既有 conf、无重装 nginx；`systemctl restart` 仅作用于本项目 `error-learn-api`
  - 端口替换静态比对：`error-learn.conf` 中 `127.0.0.1:8000` 共 4 处（2 处 `proxy_pass` + 2 处注释）、`error-learn-api.service` 中 `--port 8000` 共 1 处，均被 `deploy.sh` 的对应 sed 表达式覆盖
  - 教程事实与代码一致：`/api/v1/health`、`/static` ↔ `UPLOADS_DIR`、`npm run build:weapp`、AppID `wx683110d829c1f0f9`、`TARO_APP_API_BASE`
- **待办（不阻塞，阻塞上线）**：① 按教程 §3 完成现状勘察并记录 4 项结论；② 替换域名与证书占位；③ 独立 RDS 建库 `error_learn` 并把 ECS 内网 IP 加入白名单
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md deploy/deploy.sh`；本次未改动其它文件

---

## docs-20261015-部署教程小白版

- **编号**：docs-20261015-部署教程小白版
- **日期**：2026-10-15
- **背景**：用户为**零基础**，明确反馈"不知道怎么装到云服务器上""不知道去哪里执行代码新建数据库"。上一版教程虽已按共享 ECS 场景组织，但默认读者懂命令行，未说明"命令在哪个窗口执行"、未教如何登录服务器、未给图形化建库路径、且用 `vi` 编辑配置（小白不会用）。
- **变更摘要**：
  **仅调整讲法与粒度，技术方案不变**（仍是共享 ECS + 独立 RDS + 新开备案子域名）。
  新增：① 开篇「两个窗口」区分（阿里云控制台 vs Workbench 黑框）+ 术语卡片 + 粘贴/中断保命操作；② **逐步教登录 ECS（Workbench 点选路径）**；③ 勘察命令逐条给"怎么判断"；④ **逐步教从 GitHub 克隆代码**（含"本地须先 `git push`"的前置提醒）；⑤ **控制台图形化建库 `error_learn`**（不要求写 SQL）+ 账号 + 白名单；⑥ 编辑 `.env` 主推 `nano`（附保存/退出键位），备选 `cat > ... <<'EOF'` 整段粘贴；⑦ 全文每步配 **✅ 验证点**；⑧ 新增 [附录 A 命令速查]、[附录 B 术语小词典]、附录 C 备用 SQL。
- **影响模块**：
  - 文档：`.trae/documents/部署教程.md`（**重写为"零基础版"**，14 章 + 3 附录 + 参考来源）
  - **未改动**：`deploy/**`、前端代码、后端代码
- **关联文档路径**：`.trae/documents/部署教程.md`；方案 `.trae/documents/更新部署教程-小白版.md`
- **是否待合并主 spec**：**否**（**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 命令与仓库事实逐条一致：仓库 URL `https://github.com/diamondwei2026-maker/ai-error-learn.git`（`.git/config`）、`error_learn`、`/opt/error-learn`、`127.0.0.1:8000`（可改 8080）、`/api/v1/health`、`UPLOADS_DIR` ↔ `/static` alias、`wx683110d829c1f0f9`、`npm run build:weapp`
  - 格式核对：§3~§10 每一步均含 **✅ 验证点**
  - 小白盲区覆盖：登录服务器 / 粘贴方式 / 建库位置 / `nano` 保存退出 / GitHub 拉不动备选 / 本地先 `push` —— 均已写入
- **待办（不阻塞，阻塞上线）**：① 本地先 `git push`（当前 `develop` 领先远端，否则云上拉到旧代码）；② 按 §4 勘察并记录结论；③ 建库 + 白名单
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## docs-20261015-部署教程实测排障补充

- **编号**：docs-20261015-部署教程实测排障补充
- **日期**：2026-10-15
- **背景**：用户在实际服务器（**Alibaba Cloud Linux 3 / OpenAnolis**）按教程执行时连撞两坑：① 敲 `sudo apt update && ...` 报 `sudo: apt: command not found`；② `git clone` 拉代码失败，报 `error: RPC failed; curl 7 Failed to connect to github.com port 443: Connection timed out` + `fatal: expected flush after ref listing`。经 `curl -sI` 与 `GIT_CURL_VERBOSE=1 GIT_TRACE=1` 逐层诊断，定位为**链路中间设备（DPI）拦截 git 传输**（列 ref 列表可过、`POST git-upload-pack` 被掐断）。
- **变更摘要**：
  把上述实测经验沉淀进《部署教程》，**仅文档更新，技术方案不变**（仍是共享 ECS + 独立 RDS + 新开备案子域名）：
  ① **按发行版分支安装命令**——§4 勘察新增「识别系统发行版」步骤与判断项；§5.2 装 git、§7.2 装 Python、附录 A-2/A-3 均由单一 `apt` 改为「RHEL 系（阿里云 Linux/CentOS）用 `dnf`，Ubuntu/Debian 用 `apt`」二选一，并点明本教程对应服务器为 Alibaba Cloud Linux 3（无 `apt`）。
  ② **去除 RHEL 系不存在的 `python3-venv`**——§7.2、附录 A-3 不再安装该包，改为说明「venv 内置于 python3，缺 `ensurepip` 时装 `python3-devel`」。
  ③ **重写 §5.4「下载失败怎么办」**——由原「重试 / 换 Gitee」两句话扩展为实测排障：5.4.1 三步诊断（`getent hosts` / `curl -sI` / `GIT_CURL_VERBOSE=1`）、5.4.2 镜像前缀克隆（ghproxy ×3 + gitclone）、5.4.3 zip 打包下载、5.4.4 SSH（含 `ssh.github.com:443`）、5.4.5 传输参数调优（标注对 DPI 拦截无效），并写明根因结论。
  ④ **§13.1 排障表**新增 3 条（`apt: command not found`、`No package python3-venv available`、`git clone` 的 `RPC failed`），更新「GitHub 下载慢 / 超时」条。
  ⑤ **参考来源**补 4 条（Alibaba Cloud Linux 包管理 / Git 排障开关 / GitHub SSH 443 / 第三方克隆加速代理）。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 全仓检索教程内 `apt` / `python3-venv` 残留，均为**有意保留的分支说明或提示**，无遗留的默认 `apt` 路径
  - 命令与仓库事实一致：仓库 URL `https://github.com/diamondwei2026-maker/ai-error-learn.git`、`/opt/error-learn`、`/api/v1/health`、`error_learn`、`UPLOADS_DIR` ↔ `/static`
  - 诊断结论与实测日志一致：`curl -sI https://github.com` → `HTTP/2 200`；verbose 显示 `POST git-upload-pack` 挂起约 30s 后收到 `close notify`，重连同 IP 超时
- **待办（不阻塞，阻塞上线）**：按修正后的命令重跑 §5.2 / §7.2；`git clone` 优先走 §5.4.2 镜像前缀
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## docs-20261015-部署教程下载通道实测修订

- **编号**：docs-20261015-部署教程下载通道实测修订
- **日期**：2026-10-15
- **背景**：承接上条 `docs-20261015-部署教程实测排障补充`，用户在服务器上**实际执行**「下载代码 → 建环境」时又暴露三处需用真实结果修正/落地的地方：① `cd /opt/error-learn/server` 报 `No such file or directory`，实为 clone 从未成功；② 上一版给的镜像域名 `ghproxy.com` 在本机**不可用**，而 `gh-proxy.com` 实测可用；③ zip 打包方式虽已写入，但缺"验证下载成败 + 解压改名"的可照做步骤。
- **变更摘要**：
  按实测结果修订《部署教程》的**代码下载章节**（§5.3 / §5.4）及相关交叉引用，**仅文档更新，技术方案不变**：
  ① §5.3 主命令补 **`-b develop`**（本项目最新代码在 `develop`，避免拉到默认分支的旧代码）；新增「`ls` 报 `No such file or directory` = 代码没下载成功，不是路径写错」的醒目提示。
  ② §5.4.2 标注**本机实测可用域名 `gh-proxy.com`** 并置于首位，其余域名列为备选；补「本项目实测为公开仓库」结论。
  ③ §5.4.3 打包下载升级为**可照做的两步法**：下载用 `curl ... -w "HTTP:%{http_code} size:%{size_download}"` 自证成败（实测 `HTTP:200 size:913217`）；解压用 `unzip -d /opt` + `mv ai-error-learn-develop error-learn`；并提示 `\` 续行符不得带尾随空格、zip 快照不含 `.git`。
  ④ §12 运维补「zip 方式无 `.git`，`git pull` 不可用」的对应处理。
  ⑤ §13.1 排障表新增 2 条（`cd ... No such file or directory`、`unzip` 找不到 zip）。
  ⑥ 附录 A-2 命令同步为镜像 + `-b develop`，并附 zip 备选。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 实测数据入库：`curl -L -o /tmp/error-learn.zip -w ... https://gh-proxy.com/.../develop.zip` → `HTTP:200 size:913217`；解压后目录名为 `ai-error-learn-develop`
  - 失败数据入库：`ghproxy.com` 域名在本机下载失败；`/opt/error-learn` 不存在导致 `cd` 报错
  - 交叉引用核对：§5.3 → §5.4、§5.4.2 ↔ §5.4.3、§12 → §5.4.3/§5.4.2、§13.1 → §5.4 锚点均可跳转
- **待办（不阻塞，阻塞上线）**：本地 `develop` 先 `git push` 后再重新下载，确保服务器为最新代码；继续按 §7.2（`dnf`）建环境
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## docs-20261016-部署教程Python版本排障

- **编号**：docs-20261016-部署教程Python版本排障
- **日期**：2026-10-16
- **背景**：用户在服务器执行 `./.venv/bin/python -m pip install --upgrade pip`，只得到 `Requirement already satisfied: pip in ./.venv/lib/python3.6/site-packages (21.3.1)`。定位为**服务器系统 `python3` 过旧（Python 3.6）**：`21.3.1` 是最后一个支持 Python 3.6 的 pip，更高版本均要求 ≥3.7，故“无更新可装”；且本项目要求 Python ≥ 3.8（`fastapi>=0.110` / `sqlalchemy>=2.0` / `pytest>=8.0`），3.6 环境根本装不上依赖。升 pip 无解，须换 Python 重建 venv。
- **变更摘要**：
  将经验沉淀进《部署教程》，**仅文档更新，技术方案不变**：
  ① §7.2 拆为 **7.2.1 先检查 Python 版本**（含“≥3.8 合格 / 3.6、3.7 太旧”判断表）、**7.2.2 正常安装**、**7.2.3 Python 太旧时装新版（python3.11）并 `rm -rf .venv` 重建**；
  ② §4 现状勘察新增 ⑨「`python3 --version`」及判断项；
  ③ §13.1 排障表新增 2 条（pip 只回 `already satisfied`、pip 路径含 `python3.6`）；
  ④ 附录 A-3 补 `python3 --version` 前置检查与 `rm -rf .venv`；
  ⑤ 提示 `deploy/deploy.sh` 的 `python3 -m venv .venv` 不校验版本，须先按 §7.2.1 检查。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）；`deploy/**` 与前后端代码**未改动**
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：症状（`python3.6` + `21.3.1`）与结论（pip 21.3.1 = Python 3.6 末代版本）、项目依赖最低 Python 版本（fastapi 0.110 / sqlalchemy 2.0 / pytest 8）一致；新增命令均可在 RHEL 系执行
- **待办（不阻塞，阻塞上线）**：按 §7.2.1 确认服务器 Python 版本；<3.8 时按 §7.2.3 装 python3.11 并重建 venv
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## ops-20261016-deploy脚本Python版本守卫

- **编号**：ops-20261016-deploy脚本Python版本守卫
- **日期**：2026-10-16
- **背景**：接上条——`deploy/deploy.sh` 原为 `[ -d .venv ] || python3 -m venv .venv`，仅“无 venv 才建”、**不校验 Python 版本、也不校验已存 venv 版本**，导致服务器上旧 Python（3.6）建的 venv 被沿用，依赖装不上。
- **变更摘要**：
  为 `deploy/deploy.sh` 新增 Python 版本守卫（**仅部署脚本改动，不影响业务代码**）：
  ① 新增可配置项 `PYTHON_BIN`（默认空，自动探测）；
  ② 新增 `python_is_ok()`（判是否 >=3.8）与 `detect_python()`（按 python3.12→3.11→3.10→3.9→3.8→python3 顺序取首个合格项）；
  ③ `check_prereq` 前置拦截——无合格 Python 时直接 `die` 并提示安装命令，不再等装完才失败；
  ④ `setup_venv` 版本守卫——已存 `.venv` 若由旧 Python 创建，**自动 `rm -rf` 重建**；
  ⑤ 头部用法注释补 `PYTHON_BIN` 示例与 Python>=3.8 前置说明。
- **影响模块**：`deploy/deploy.sh`（唯一改动文件）；前端/后端代码、nginx/systemd 模板**未改动**
- **关联文档路径**：`deploy/deploy.sh`；配套教程 `.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（部署脚本，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：`bash -n deploy/deploy.sh` → 语法通过；`PYTHON_BIN` 空/显式两路分支均可走到 venv 创建；`python_is_ok` 对 3.6 返回非零、对 3.11 返回零（逻辑自洽）
- **待办（不阻塞，阻塞上线）**：服务器上先确保存在 >=3.8 的解释器（如 `python3.11`），再跑脚本
- **回滚方式**：`git checkout <上一可用提交> -- deploy/deploy.sh`；本次未改动其它文件

---

## docs-20261016-部署教程后端启动排障补充

- **编号**：docs-20261016-部署教程后端启动排障补充
- **日期**：2026-10-16
- **背景**：用户在阿里云 Linux 3 ECS 上按教程 §7.3~§7.4 手工部署后端时，**连续踩了 4 个教程未覆盖的坑**（均为发行版差异 / 环境差异，非代码 bug）：
  ① `sudo systemctl status` 报 **`status=217/USER`**——模板 `User=www-data` 在本机不存在（RHEL 系应为 `nginx`），进程未启动；
  ② `nano: command not found`——阿里云 Linux 3 最小化安装默认不带 nano；
  ③ 启动报 **`sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL`**——`.env` 的 `DATABASE_URL` **只填了主机名**，漏了 `mysql+pymysql://账号:密码@主机:3306/库?charset=utf8mb4` 外壳；
  ④ 启动报 **`PermissionError: '/opt/error-learn/server/uploads'`**——运行用户 `nginx` 对项目目录无写权限，`create_app` 里 `uploads_dir.mkdir()` 失败。
  最终服务成功 `active (running)`、`/api/v1/health` 返回 `{"status":"ok"}`。
- **变更摘要**：
  将上述实测经验沉淀进《部署教程》，**仅文档更新，技术方案不变**：
  ① §7.3 新增 `nano: command not found` 处理（装 nano / 改用 vi 键位）；`DATABASE_URL` 行加粗强调"必须是一整条连接串"，并新增 **正 / 误对比**示例与密码特殊字符 URL 编码提示；
  ② §7.4 新增"先 `ps -o user= -C nginx` 确认运行用户"；sed 命令补 `User=www-data→nginx` / `Group=` 替换并**合成一行**；新增"给运行用户开 uploads 写权限"步骤；解释 `217/USER` 成因；
  ③ §13.1 排障表新增 4 条（`nano` 缺失、`217/USER`、`Could not parse SQLAlchemy URL`、`PermissionError uploads`）。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）；`deploy/**` 与前后端代码**未改动**
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 4 个报错关键字与实测日志逐条对应（`status=217/USER`、`nano: command not found`、`Could not parse SQLAlchemy URL`、`PermissionError ... uploads`）
  - 修复后实测：`systemctl status` → `active (running)`；`curl 127.0.0.1:8000/api/v1/health` → `{"status":"ok"}`；`Python 3.11.13` + `uvicorn 0.54.0`
  - §7.4 的 `User=nginx` 与 `deploy/systemd/error-learn-api.service` 模板默认 `User=www-data` 对应；`deploy.sh` 的 `RUN_USER` 机制覆盖同一场景
- **待办（不阻塞，阻塞上线）**：按 §7.4 为运行用户开 uploads 写权限；继续 §8 接入 Nginx
- **安全提醒**：排查过程中用户曾贴出明文 `WECHAT_APP_SECRET` / `JWT_SECRET`，建议上线稳定后重置这两项
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## docs-20261016-部署教程SSL证书排障沉淀

- **编号**：docs-20261016-部署教程SSL证书排障沉淀
- **日期**：2026-10-16
- **背景**：用户在实际服务器（Alibaba Cloud Linux 3 / Nginx 1.24.0，且**已用 certbot 管理 story 站点证书**）为子域名 `errorlearn.diamondwtech.com` 接入 HTTPS 时，连撞教程未覆盖的证书类坑：① `curl -v` 报 `SSL: no alternative certificate subject name matches target host name 'errorlearn...'`（`curl: (51)`）——实为该域名在 Nginx **未配 server 块**，请求落到 `server_name _;` 兜底站、返回了 story 站证书；② `certbot --nginx` 两次报 `Invalid response from ... 403`——80 端口兜底站的 `deny` 正则拦截 `.well-known`；③ `certbot --manual --preferred-challenges dns` 报 `NXDOMAIN`——TXT 未添加即回车，且**每次重跑值都会变**；④ `dig` / `nslookup` 均 `command not found`；⑤ `Another instance of Certbot is already running.`——锁文件残留；⑥ Workbench「新建终端」失败。另有用户两次把 `curl` 网址误写成反引号。原 §9 只给了 acme.sh + DNS-01 一条路，未覆盖 certbot 方案与上述排障。
- **变更摘要**：
  将本轮实测经验沉淀进《部署教程》，**仅文档更新，技术方案不变**：
  ① **§9 证书章节重构为"先选工具、再分方案"**——新增 9.1 工具二选一判断（有 certbot 用 certbot / 有 acme.sh 用 acme.sh / 都没有装 certbot，明确"**别混用**"）；9.2 方案 A「certbot」（9.2.1 DNS-01 手动验证：含 TXT 主机记录写法 `_acme-challenge.<前缀>`、`curl` DoH 查询生效、回车时机与"重跑值会变"告警；9.2.2 `certbot --nginx` 的 403 成因与 `^~` location 绕过；9.2.3 certbot 常见报错表；9.2.4 `certbot-dns-aliyun` 自动续期）；9.3 方案 B「acme.sh」（原内容）；**9.4 让 Nginx 用上证书并验收**——强调"证书先在位、再配 Nginx"，并给出 certbot 证书路径下完整的 80 跳转 + 443 配置块。
  ② **§8 新增 8.4「常见坑：报证书域名不匹配」**——解释 `SSL: no alternative certificate subject name` / `curl: (51)` 的成因（落到 `server_name _;` 兜底站）与一步定位命令 `nginx -T | grep -nE "server_name|ssl_certificate"`。
  ③ **§4 现状勘察** 新增 ⑩ `getenforce`（SELinux）及判断项；第 ⑥ 项证书工具改为"二选一"口径。
  ④ **§12 运维** 证书查看补 certbot（`certbot certificates`）与续期说明（手动 DNS 方式不自动续）；**§14 回滚** 证书项补 certbot（`certbot delete --cert-name`）。
  ⑤ **§13.1 排障表**新增 8 条、**§13.3 共享服务器专属**新增 3 条；**附录 A-4** 补 certbot 分支提示、**A-5** 拆为 A-5A certbot / A-5B acme.sh；**参考来源**补 4 条（Certbot / Let's Encrypt 挑战类型 / certbot-dns-aliyun / Nginx location 优先级）并将校对日期更新为 2026-10-16。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）；`deploy/**` 与前后端代码**未改动**
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 报错关键字与实测日志逐条对应（`SSL: no alternative certificate subject name`、`curl: (51)`、`Invalid response ... 403`、`NXDOMAIN looking up TXT`、`command not found`、`Another instance of Certbot is already running.`）
  - 事实一致：`server_name _;` 兜底站观察、Nginx `1.24.0`（决定必须用 `listen 443 ssl http2;`）、服务器已装 `certbot`、证书路径 `/etc/letsencrypt/live/<domain>/`
  - 命令可在 RHEL 系执行：`curl -s "https://223.5.5.5/resolve?...&type=TXT"`、`sudo rm -f /var/lib/letsencrypt/.certbot.lock`、`sudo certbot certificates`、`sudo dnf install -y bind-utils`
  - 新增锚点（§8.4 / §9.2 / §9.2.1~9.2.4 / §9.4）与文内交叉链接一一对应
- **待办（不阻塞，阻塞上线）**：按 §9.2.1 完成证书签发 → 按 §9.4 写 443 配置 → `curl` 复测 `{"status":"ok"}`
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## cfg-20261016-微信AppID切换

- **编号**：cfg-20261016-微信AppID切换
- **日期**：2026-10-16
- **变更摘要**：将微信小程序 AppID 由 `wx683110d829c1f0f9` 切换为 `wxf7fbaf8d9a6f7296`。同步后端默认值、示例配置、测试断言与相关文档；`server/.env`（不入库）此前已由用户改为新值，配置来源与代码默认值现已一致。
- **影响模块**：
  - 前端：`client/project.config.json`
  - 后端：`server/app/config.py`、`server/.env.example`、`server/tests/test_config.py`
  - 部署：`deploy/env.production.example`
  - 文档：`.trae/documents/部署教程.md`、`.trae/specs/mvp-reverse-docs/spec.md`、`.trae/docs/increments/incr-20261014-用户系统/spec.md`
- **关联文档路径**：无新增文档；见上述改动文件
- **是否待合并主 spec**：**否**（仅配置值替换，未改结构；主 spec 中该值为事实描述，已同步）
- **验证结果**：全仓检索确认除本 change-log 历史记录外无旧 AppID 残留；`server/tests/test_config.py::test_user_system_defaults` 断言与新默认值一致
- **回滚方式**：`git checkout <上一可用提交> -- client/project.config.json server/app/config.py server/.env.example deploy/env.production.example server/tests/test_config.py .trae/documents/部署教程.md .trae/specs/mvp-reverse-docs/spec.md .trae/docs/increments/incr-20261014-用户系统/spec.md`

---

## cfg-20261016-启用组件按需注入

- **编号**：cfg-20261016-启用组件按需注入
- **日期**：2026-10-16
- **背景**：小程序代码上传微信后「代码质量」扫描提示 **「启用组件按需注入：未通过」**。该扫描项对应官方《小程序性能优化指南》第 12 条【必须】——须在 `app.json` 配置 `"lazyCodeLoading": "requiredComponents"` 开启组件按需注入。本仓库此前全局检索无任何 `lazyCodeLoading` 配置，故命中。
- **变更摘要**：在 Taro 全局应用配置 `client/src/app.config.ts` 顶层新增 `lazyCodeLoading: 'requiredComponents'`（构建后注入 `dist/app.json`），开启小程序组件按需注入特性。**无业务逻辑改动、无 UI 改动、后端零改动。**
- **影响模块**：
  - 前端（`client/`）：修改 `src/app.config.ts`（新增 `lazyCodeLoading: 'requiredComponents'`）
- **关联文档路径**：无新增文档；官方依据《小程序性能优化指南》第 12 条，`https://developers.weixin.qq.com/miniprogram/dev/framework/ability/lazyload.html`
- **是否待合并主 spec**：**否**（配置项修复，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：`npm run build:weapp` → **构建成功**（31.15s）；产物 `client/dist/app.json` 已含 `"lazyCodeLoading":"requiredComponents"`。构建输出中的 `mini-css-extract-plugin Conflicting order` 为既有告警，不影响构建（exit 0）
- **注意事项**：若后续引入插件组件或使用分包异步化/动态组件，可能需额外配置 `componentPlaceholder`；该配置仅对微信端（weapp）生效
- **回滚方式**：移除 `client/src/app.config.ts` 中的 `lazyCodeLoading` 一行即可恢复

---

## docs-20261016-部署教程隐私指引入口更新

- **编号**：docs-20261016-部署教程隐私指引入口更新
- **日期**：2026-10-16
- **背景**：微信小程序管理后台改版，旧入口「设置 → 功能设置 → 用户隐私保护指引」已**移除**，教程 §11.2 原路径失效，读者按旧路径找不到入口。
- **变更摘要**：仅文档更新，技术方案不变。将 §11.2 路径更新为新版后台路径「登录微信公众平台 → 左下角头像 → 账号设置 → 服务内容声明 → 用户隐私保护指引」，并补充：① 旧入口已移除；② 该入口仅对已发布上线的小程序可见，未上线可在**提交代码审核**页面的「用户隐私保护指引设置」处填写。
- **影响模块**：文档 `.trae/documents/部署教程.md`（唯一改动文件）；前后端代码与 `deploy/**` 未改动
- **关联文档路径**：`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档更新，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：联网核实（微信官方知识库 + 开发者社区帖，均一致）——现网版入口为「账号设置 → 服务内容声明 → 用户隐私保护指引」；提审版入口为「版本管理 → 提交代码审核 → 用户隐私保护指引设置」
- **回滚方式**：`git checkout <上一可用提交> -- .trae/documents/部署教程.md`；本次未改动其它文件

---

## incr-20261016-内容安全接入

- **编号**：incr-20261016-内容安全接入
- **日期**：2026-10-16
- **背景**：上线物料缺口清单 C3「内容安全未接入」——全仓此前**零实现**，且**没有微信 `access_token` 获取/缓存逻辑**（`wechat_service.py` 只有 `code2session`），无法调用 `msgSecCheck`。本次落地微信内容安全接入，覆盖全部 UGC 写入点。
- **变更摘要**：
  接入微信内容安全，三类 UGC 全覆盖（上游方案 `.trae/documents/微信内容安全接入改造方案.md`）：
  ① **文本**——`msgSecCheck` v2：昵称（scene=1 资料，`PATCH /user/me` 同步拦截，返回 2007）；错题题干/答案（scene=3 论坛，**保存前预检** `POST /security/text-check` 返回 3002 + **服务端 `sync/push` 兜底**列入 `rejected` 且不落库）。
  ② **图片**——`mediaCheckAsync` v2：头像上传后异步送检（需 `PUBLIC_BASE_URL`），结果经**消息推送回调** `GET/POST /api/v1/wechat/callback`（明文模式 SHA1 验签，兼容 JSON/XML）匹配 `trace_id`；命中 `risky` → 删除头像文件 + 清空 `avatar_url`。
  ③ **前置能力**——新增 `ContentSecurityService`：`getStableAccessToken` 获取 + 内存缓存（提前 300s 失效、40001 清缓存重试一次）。
  ④ **降级策略**：未配置密钥 / 接口报错 / 无权限 / IP 未白名单 / `suggest=review` → **放行 + 记日志**，绝不阻塞用户写入。
  ⑤ 新增表 `media_check_record`（trace_id 唯一）用于异步结果匹配；`init_db` 已登记。
  **无 UI 结构/视觉改动**（保存错题时仅多一次网络预检 + 命中 toast）→ 按项目规则**未触发双阶段原型流程**；**未修改** `.trae/specs/mvp-reverse-docs/`。
- **影响模块**：
  - 后端（`server/`）
    - 新增：`app/services/content_security.py`、`app/api/security.py`、`app/api/wechat_callback.py`、`app/models/media_check.py`、`tests/test_content_security_api.py`
    - 修改：`app/config.py`（+`CONTENT_SECURITY_ENABLED`/`PUBLIC_BASE_URL`/`WECHAT_CALLBACK_TOKEN`/`CONTENT_SECURITY_TIMEOUT` 与 `content_security_ready`/`media_check_ready`）、`app/errors.py`（+`CODE_NICKNAME_RISK=2007`、`CODE_SYNC_CONTENT_RISK=3002`）、`app/models/schemas.py`（+`TextCheckRequest`）、`app/db/session.py`（登记新模型）、`app/api/user.py`（昵称校验 + 头像异步送检 + 注销时清理送检记录）、`app/api/sync.py`（push 兜底校验 + `rejected` 字段）、`app/main.py`（装配 + 启动告警）、`.env.example`、`tests/conftest.py`（autouse `stub_content_security` 夹具 + 回调 Token/公网基地址）、`tests/test_config.py`（+4 例内容安全配置）
  - 前端（`client/`）
    - 新增：`src/services/securityService.ts`
    - 修改：`src/constants/index.ts`（+`CONTENT_CODE`/`CONTENT_ERROR_MESSAGES`）、`src/services/request.ts`（`messageFor` 兜底内容安全文案）、`src/pages/edit/index.tsx`（保存前预检：命中 3002 拦截，异常降级放行）、`src/services/syncService.ts`（`PushResult.rejected` + 告警日志）
  - 部署：`deploy/env.production.example`（补内容安全四项变量）
  - 文档：`.trae/documents/微信内容安全接入改造方案.md`、`.trae/docs/increments/incr-20261016-内容安全接入/{方案.md,tasks.md,checklist.md}`
- **关联文档路径**：`.trae/documents/微信内容安全接入改造方案.md`；`.trae/docs/increments/incr-20261016-内容安全接入/`
- **是否待合并主 spec**：**否**（普通增量走 `/plan`，**未修改** `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 后端：`.venv\Scripts\python.exe -m pytest` → **105 passed**（原 80 + 新增 25，无回归）
    - ⚠️ 说明：`server/.env` 的 `DATABASE_URL` 仅填主机名（非合法连接串），会导致导入 `app.main` 时 `create_app()` 失败。本次以**临时移开 `.env`** 的方式完成回归，跑完已**原样还原**（既有环境问题，非本次引入）
  - 前端：`npx tsc --noEmit` → 无新增类型错误（仅全仓既有的 `React` 未使用基线告警 + Taro 依赖类型声明告警）；`npm run build:weapp` → **构建成功**（exit 0，仅有既有的 mini-css-extract-plugin Conflicting order 告警）
- **上线前置条件（不阻塞编码，阻塞生效）**：
  1. MP 后台「开发管理 → 开发设置 → **IP 白名单**」加入 ECS 公网出口 IP（否则 `getStableAccessToken` 报 `40164`，内容安全整体降级放行）
  2. MP 后台「**消息推送**」：URL `https://errorlearn.diamondwtech.com/api/v1/wechat/callback`、Token 与 `WECHAT_CALLBACK_TOKEN` 一致、数据格式 JSON、加解密方式**明文模式**
  3. `server/.env` 配置 `CONTENT_SECURITY_ENABLED=true`、`PUBLIC_BASE_URL=https://errorlearn.diamondwtech.com`、`WECHAT_CALLBACK_TOKEN=<与后台一致>`
  4. 域名已备案且 `https://<域名>/static/avatars/*` 可被外网直接下载（`mediaCheckAsync` 由微信服务器拉取）
  5. 注意：**未上架小程序文本检查限 100 次/天**（已通过"仅新增/变更项送检"限流）
- **回滚方式**：`server/.env` 置 `CONTENT_SECURITY_ENABLED=false` → 全链路立即降级放行（无需改代码）；代码级 `git checkout <上一可用提交> -- server/ client/`；新增表 `media_check_record` 为纯追加，无需回滚；微信侧清空「消息推送」配置即断开回调

---

## fix-20261016-开发环境网络异常修复

- **编号**：fix-20261016-开发环境网络异常修复
- **日期**：2026-10-16
- **背景**：开发环境（微信开发者工具 + 本地后端）执行「**微信一键登录**」时提示「网络异常」。排查发现三层问题：
  ① **微信侧拦截**——`client/project.config.json` 的 `setting.urlCheck: true`（= 开发者工具「校验合法域名」开启），而 dev 后端为 `http://192.168.60.37:8000`（IP + HTTP，非白名单域名）→ 请求在平台层被拒，前端落到 [request.ts L84-87](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L84-L87) 的「网络异常，请检查网络后重试」；
  ② **后端配置非法且不可达**——`server/.env` 的 `DATABASE_URL` 只填主机名 `rm-bp10q72z75es2z24f.mysql.rds.aliyuncs.com`（缺 `scheme://账号:密码@主机:3306/库`）→ 后端一旦加载即 `Could not parse SQLAlchemy URL` 启动失败；且该主机解析为内网 `172.26.250.233`，本机 TCP 3306 **实测 6s 超时不可达**，登录链路（必经 `find_or_create_user` 写库）会挂到前端 15s 超时，同样表现为「网络异常」；
  ③ **遗留进程与配置漂移**——8000 端口上遗留 **2026/10/14** 与 **2026/10/15** 两组 uvicorn 实例争用端口，且在跑的是**旧代码**（`/api/v1/security/text-check`、`/api/v1/wechat/callback` 均 404）。
- **变更摘要**：
  **仅修复本机开发环境配置与进程，未改动任何业务代码、无 UI 改动、后端/前端源码零改动**：
  ① `server/.env`：`DATABASE_URL` 改回本地口径 `sqlite:///./app.db`（沿用既有 `server/app.db` 数据，不丢数据）；新增 `CONTENT_SECURITY_ENABLED=false`（开发期消除对微信接口 / IP 白名单的依赖与额外延迟）。改前已备份 `server/.env.bak`；
  ② 停止 8000 端口上两组遗留 uvicorn 进程（PID 18536 / 17032 / 27020、7296 / 17904），释放端口；
  ③ 用项目 `.venv` 干净启动**单实例**后端：`uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env`；
  ④ 输出排查与修复文档 `.trae/documents/开发环境网络异常排查与修复方案.md`，并生成根目录会话任务清单 `todo.md`。
- **影响模块**：
  - 本机环境：`server/.env`（不入库，`.gitignore` 已忽略）、`server/.env.bak`（备份）、运行中的 uvicorn 进程
  - 文档：`.trae/documents/开发环境网络异常排查与修复方案.md`（新增）、`todo.md`（根目录，新增）
  - 代码：`server/**`、`client/**` **均未改动**
- **关联文档路径**：`.trae/documents/开发环境网络异常排查与修复方案.md`
- **是否待合并主 spec**：**否**（环境/配置修复，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 启动日志无 `Could not parse SQLAlchemy URL`、无 `address already in use`，`Application startup complete`
  - `GET /api/v1/health` → 200 `{"status":"ok"}`
  - `GET /openapi.json` 已含 `/api/v1/security/text-check` 与 `/api/v1/wechat/callback` → 确认新代码已加载生效
  - `netstat -ano` 确认 8000 端口仅剩**单实例**（PID 13208）监听
  - 已排除项：系统代理（`127.0.0.1:7897`，`ProxyOverride` 含 `192.168.*`，实测直连与走代理均 HTTP 200）、VPN 虚拟网卡（`LetsTAP` 未 Up）、本机 IP 与 `client/.env.development` 不一致（两者均为 `192.168.60.37`）
- **待办（需用户侧操作，阻塞最终验收）**：① 开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」并清缓存重编译；② 复现微信一键登录确认恢复；③ 若仍返回 `code=2004`，核对 MP 后台 `WECHAT_APP_SECRET` 是否属于 AppID `wxf7fbaf8d9a6f7296`
- **回滚方式**：`server/.env` 用 `server/.env.bak` 覆盖还原即可；进程按原命令重启；本次未改动任何入库代码文件（仅新增两份文档与根目录 `todo.md`）

---

## fix-20261016-后端启动端口占用（WinError 10013）修复

- **编号**：fix-20261016-后端启动端口占用（WinError 10013）修复
- **日期**：2026-10-16
- **背景**：启动 Python 后端时报 `ERROR:    [WinError 10013] 以一种访问权限不允许的方式做了一个访问套接字的尝试。`（易被误判为权限/防火墙问题）。排查确认根因是**端口占用**：
  - 8000 端口已被一个**遗留 uvicorn 实例**占用（PID 316 = `server\.venv\Scripts\python.exe` 启动器；PID 13208 = 其子进程 `D:\python3.12\python.exe`，真正 LISTEN 的进程；两者均启动于 `2026/10/16 16:03:57`，为上一次会话为验收而拉起、未随会话回收的实例）。
  - **为什么报 10013 而非 10048**：uvicorn 0.54.0 在 bind 前对监听 socket 设置了 `SO_REUSEADDR`（`server/.venv/Lib/site-packages/uvicorn/config.py` L600-606 → `bind` 失败即 `logger.error(exc); sys.exit`）。Windows 的 `SO_REUSEADDR` 语义与 Linux 不同：端口已被他人正常绑定时，**带** `SO_REUSEADDR` 的二次 bind 被拒为 `WSAEACCES(10013)`，**不带**才是 `WSAEADDRINUSE(10048)`。已用 `server\.venv` 的 Python 在同机实测复现该差异。
  - 已排除：Hyper-V/WinNAT 保留端口段（`netsh interface ipv4 show excludedportrange protocol=tcp` 仅 `5357-5357`，`winnat` 服务 `Stopped`）、启动 host/端口写错（与 `server/app/main.py` 注释、`client/package.json` 脚本、`client/.env.development` 的 `192.168.60.37:8000` 一致）、`.env` 配置非法（`DATABASE_URL=sqlite:///./app.db` 上次已修正，且遗留实例能用该 `.env` 正常启动）。
- **变更摘要**：**仅处置本机进程，未改动任何业务代码、配置与部署文件（零文件改动）**：
  ① 实测确认 8000 端口占用者及其父进程（PID 13208 / 316）；
  ② `Stop-Process -Force` 成对停止父/子进程，释放端口；
  ③ 校验释放：`netstat` 无 `:8000` 输出，且 venv Python 对 `0.0.0.0:8000` bind 探测输出 `8000 FREE`；
  ④ 用项目既有脚本 `npm run server` 干净启动**单实例**（依赖检查通过 → 加载 `.env` → `--reload` 热重载），后续改后端代码可自动重启。
- **影响模块**：
  - 本机运行环境：8000 端口上的进程（遗留实例已停止，改为带 `--reload` 的新单实例）
  - 代码/配置/部署：**均未改动**（`server/**`、`client/**`、`server/.env`、`deploy/**` 零改动）
  - 文档：`.trae/documents/后端启动失败WinError10013修复方案.md`（新增）、`todo.md`（根目录，刷新）
- **关联文档路径**：`.trae/documents/后端启动失败WinError10013修复方案.md`
- **是否待合并主 spec**：**否**（环境/进程修复，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 启动日志：`后端依赖检查通过` → `Uvicorn running on http://0.0.0.0:8000` → `Application startup complete`，**无** `[WinError 10013]`、**无** `[Errno 10048]`
  - `GET /api/v1/health` → `200 {"status":"ok"}`
  - `GET /openapi.json` 含 `/api/v1/security/text-check`、`/api/v1/wechat/callback`
  - `Get-NetTCPConnection -LocalPort 8000` → 仅 1 条 `0.0.0.0:8000 Listen`（PID 5616，`--reload` reloader），无父子双实例残留
- **回滚方式**：停掉新实例后按原命令重启即可（本次未改动任何文件，无需文件级回滚）；文档与 change-log 段落可按需删除
- **备注**：同类「遗留 uvicorn 占用 8000」问题已连续三次出现（10/14、10/15、10/16）。本次按用户决定**未**加入启动前端口占用预检（如需防复发，可在 `client/package.json` 的 `server` 脚本前置一步占用检测）

---

## fix-20261016-开发联调误用生产构建（API_BASE 指向占位域名）

- **编号**：fix-20261016-开发联调误用生产构建（API_BASE 指向占位域名）
- **日期**：2026-10-16
- **背景**：微信开发者工具点「微信一键登录」仍报「网络异常」，Console 实为 `POST https://api.example.com/api/v1/auth/login net::ERR_NAME_NOT_RESOLVED`。**前一条 `fix-20261016-开发环境网络异常修复` 的三个假设（微信域名校验 / DB 非法 / 旧实例）均已不再是原因**，本次为**新根因**。
- **根因（已实测确认）**：`client/dist/` 是**生产模式**构建产物，`API_BASE` 被编译成**占位域名** `https://api.example.com`，该域名不存在 → DNS 解析失败 → `Taro.request` 抛错 → 命中 [request.ts L84-87](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L84-L87) 的「网络异常，请检查网络后重试」。**请求从未到达后端，与后端 / DB / 域名校验无关。**
  - 证据 1：`client/dist/common.js` 修改时间 **2026/10/16 16:12:06**，其中 `API_BASE = "https://api.example.com"`、`192.168.60.37` 出现 0 次。
  - 证据 2：[cli.js L66-L68](file:///d:/Users/weij/ai-error-learn/client/node_modules/@tarojs/cli/dist/cli.js#L66-L68) `NODE_ENV = args.watch ? 'development' : 'production'`；[cli.js L77-L79](file:///d:/Users/weij/ai-error-learn/client/node_modules/@tarojs/cli/dist/cli.js#L77-L79) `mode = args.mode || NODE_ENV` → 按 mode 加载 `.env.<mode>`。故 `taro build --type weapp`（**无** `--watch`）= 生产模式 → 加载 `.env.production`（`https://api.example.com`）。
  - 已排除：后端（`0.0.0.0:8000` 监听、`/api/v1/health` 200、登录探测返回预期 `2004`）、`server/.env`（已是 `sqlite:///./app.db` + `CONTENT_SECURITY_ENABLED=false`）、微信域名校验（[project.private.config.json L6](file:///d:/Users/weij/ai-error-learn/client/project.private.config.json#L6) `urlCheck: false`，私有配置优先于 `project.config.json` 的 `true`）、本机 IP（`192.168.60.37`，与 `.env.development` 一致）。
- **变更摘要**：
  ① 以**开发模式**重新构建：`client` 下 `npm run dev:weapp`（= `taro build --type weapp --watch`，watch 常驻），覆盖 `dist/`，使 `API_BASE` 改回 `http://192.168.60.37:8000`；
  ② 清理 8000 端口上的**两组冗余 uvicorn 实例**（PID 30092/5616、14188/24640 及其 `multiprocessing-fork` 子进程），改用 `npm run server` 启动**单实例**（reloader 27284 / server 10300）；
  ③ 【防复发·唯一的代码改动】[constants/index.ts](file:///d:/Users/weij/ai-error-learn/client/src/constants/index.ts#L30-L39) 在 `API_BASE` 定义后新增 4 行 `console.error` 守卫：当 `API_BASE` 仍含占位域名 `api.example.com` 时显式告警，提示改用 `npm run dev:weapp`；
  ④ 输出方案文档 `.trae/documents/微信小程序网络异常修复-生产构建误用.md`，并为上一版排查文档补**勘误更正**，刷新根目录 `todo.md`。
- **影响模块**：
  - 前端代码：`client/src/constants/index.ts`（**仅新增 4 行 `console.error` 守卫**，无业务逻辑 / UI / 类型签名变化）
  - 前端产物：`client/dist/**`（由生产构建产物替换为开发构建产物）
  - 本机运行环境：8000 端口 uvicorn 实例（两组冗余 → 单实例）
  - 文档：`.trae/documents/微信小程序网络异常修复-生产构建误用.md`（新增）、`.trae/documents/开发环境网络异常排查与修复方案.md`（补勘误）、`todo.md`（刷新）
  - 未改动：`server/**`、`client/.env.*`、`client/project*.json`
- **关联文档路径**：`.trae/documents/微信小程序网络异常修复-生产构建误用.md`
- **是否待合并主 spec**：**否**（构建/环境修复，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 构建：`npm run dev:weapp` 完成并进入 `Watching...`（无构建失败；仅有既有的 CSS chunk order warning）
  - 产物：`client/dist/common.js` 抽出 **`API_BASE = "http://192.168.60.37:8000"`**；`http://192.168.60.37:8000` 出现 2 次，`https://api.example.com` 仅剩 1 次且为**注释文本**（非赋值）
  - 类型：`npx tsc --noEmit` **未新增**任何 `src/` 类型错误（仅全仓既有的 `React` 未使用告警与 `node_modules` 的 `.d.ts` 既有报错）
  - 后端：`Get-NetTCPConnection -LocalPort 8000` → 单条 `0.0.0.0:8000 Listen`；`http://192.168.60.37:8000/api/v1/health` → `{"status":"ok"}`；`POST /api/v1/auth/login`（假 code）→ `{"code":2004,...}`（预期）
- **待办（需用户侧操作，阻塞最终验收）**：开发者工具 → **工具 → 清除缓存 → 全部清除** 后**重新编译**；复核 **详情 → 本地设置**「不校验合法域名…」已勾选；复现登录确认请求域名为 `192.168.60.37:8000`（若仍为 `api.example.com` 说明 IDE 仍加载旧产物，需再清缓存重编译）
- **回滚方式**：`git checkout <上一可用提交> -- client/src/constants/index.ts` 撤销守卫；产物重跑 `npm run dev:weapp` 或 `npm run build:weapp` 覆盖 `dist/`；后端按原命令重启。**未改动任何后端代码与配置文件。**

---

## fix-20261016-体验版误用开发构建（登录报网络异常）

- **编号**：fix-20261016-体验版误用开发构建（登录报网络异常）
- **日期**：2026-10-16
- **背景**：**生产环境体验版**（开发者工具「上传」后真机扫码）点「微信一键登录」报「网络异常」。与上一条 `fix-20261016-开发联调误用生产构建` 属**同一类根因的另一次发作**，但发生在生产/体验版链路上。
- **根因（已实测确认）**：`client/dist/` 当时是**开发模式**构建产物（`common.js` 抽出 `API_BASE = "http://192.168.60.37:8000"`，构建时间 `2026/10/16 16:16:19`），被直接上传为体验版 → 真机访问局域网 IP + HTTP：不在微信服务器域名白名单、非 HTTPS、手机不在该局域网时不可达 → `Taro.request` 失败 → 命中 [request.ts L84-87](file:///d:/Users/weij/ai-error-learn/client/src/services/request.ts#L84-L87) 的「网络异常，请检查网络后重试」。
  并存的第二个必爆点：`client/.env.production` 仍是占位域名 `https://api.example.com`，**即使改回生产构建也连不上**。两者必须同时修。
  掩盖因素：开发者工具 [project.private.config.json L6](file:///d:/Users/weij/ai-error-learn/client/project.private.config.json#L6) `urlCheck: false` **仅对本机模拟器生效**，体验版/正式版在真机强制校验合法域名。
- **变更摘要**：
  **仅前端链路（用户确认「服务器与域名侧视作就绪」），无后端改动、无 UI/业务逻辑改动**：
  ① `client/.env.production`：`TARO_APP_API_BASE` 由占位域名改为真实生产域名 `https://errorlearn.diamondwtech.com`（无尾斜杠、无端口），并补注释强调"上传体验版前必须用生产构建"；
  ② 以**生产模式**重新构建 `client/dist/`（`npm run build:weapp`，**不带** `--watch`）；
  ③ 【防复发·唯一的代码改动】[constants/index.ts](file:///d:/Users/weij/ai-error-learn/client/src/constants/index.ts#L41-L50) 在既有占位域名守卫之后，新增生产构建守卫：`NODE_ENV === 'production'` 且 `API_BASE` 非 HTTPS 公网域名时 `console.error` 告警（覆盖"误传 dev 产物 / 占位域名"两种翻车姿势）；
  ④ 更新 [部署教程 §10](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L947-L949)（上传前必须生产构建 + 「不校验合法域名」仅本机生效的警示）、上一版排查文档加交叉引用、刷新根目录 `todo.md`。
- **影响模块**：
  - 前端（`client/`）：修改 `src/constants/index.ts`（新增 10 行守卫，无业务/UI 变化）、`.env.production`（域名由占位改为真实值）
  - 前端产物：`client/dist/**`（dev 产物 → prod 产物，`common.js` 已确认 `API_BASE = "https://errorlearn.diamondwtech.com"`、`192.168.60.37` 出现 0 次）
  - 文档：新增 `.trae/documents/体验版微信登录网络异常修复方案.md`；修改 `.trae/documents/部署教程.md`、`.trae/documents/微信小程序网络异常修复-生产构建误用.md`；`todo.md`（刷新）
  - **未改动**：`server/**`、`client/project.config.json`、`client/project.private.config.json`、`deploy/**`
- **关联文档路径**：`.trae/documents/体验版微信登录网络异常修复方案.md`
- **是否待合并主 spec**：**否**（构建/配置修复，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 构建：`npm run build:weapp` → **exit 0**（仅既有 `mini-css-extract-plugin Conflicting order` 告警）；`npx tsc --noEmit` → `src/` 无新增错误（仅 `node_modules/@tarojs/components/*.d.ts` 既有报错）
  - 产物：`dist/common.js`（`2026/10/16 16:28:16`）`API_BASE = "https://errorlearn.diamondwtech.com"`；`192.168.60.37` **0** 次；`api.example.com` 2 次且均在守卫代码内；`dist/app.json` 仍含 `lazyCodeLoading`
  - ⚠️ **未通过（阻塞真机验收，需服务器侧处理）**：本机复测 `https://errorlearn.diamondwtech.com` 全程 `curl: (35) Recv failure: Connection was reset`（TLS 握手被 reset）。**已排除本机网络因素**——对 `mp.weixin.qq.com`(200) / `api.weixin.qq.com`(404) / `www.aliyun.com`(403) 的 HTTPS 均正常；且 `curl -sk https://47.96.160.201/`（直连 IP，不带 SNI）返回 **200**、`http://errorlearn.diamondwtech.com/` 返回 **403**（未落到项目模板的 301 跳转，而是兜底站 deny）。判读：该域名在 Nginx 上**尚无（或未生效）80/443 server 块与证书**，与「域名已就绪」前提不符。
- **上线前置条件（用户侧，阻塞生效）**：
  1. 服务器侧补齐/修正 `server_name errorlearn.diamondwtech.com;` 的 80（301 跳转）+ 443（证书 + 反代）配置并 `reload nginx`；验收：手机浏览器打开 `https://errorlearn.diamondwtech.com/api/v1/health` 返回 `{"status":"ok"}`
  2. MP 后台「开发管理 → 开发设置 → 服务器域名」：`request` / `uploadFile` / `downloadFile` 均填 `https://errorlearn.diamondwtech.com`
  3. 开发者工具：清除缓存 → 重新编译 → **取消勾选**「不校验合法域名…」→ 上传（版本号自增）→ mp 后台**选为体验版** → 真机复测登录
- **回滚方式**：`git checkout <上一可用提交> -- client/.env.production client/src/constants/index.ts`；产物重新跑 `npm run dev:weapp`（本地联调）或 `npm run build:weapp`（生产）覆盖 `dist/`；本次**未改动任何后端代码与部署文件**。

---

## fix-20261016-体验版登录网络异常（续）：服务器补全 443 + "内网假象"排查沉淀

- **编号**：fix-20261016-体验版登录网络异常（续）
- **日期**：2026-10-16
- **背景**：接上一条 `fix-20261016-体验版误用开发构建`。当时把"本机 `curl https://errorlearn.diamondwtech.com` 被 reset、`http://` 返回 403"判定为**服务器未配 443/证书**并列为阻塞项。本轮联机排查后**结论更正**，并完成服务器侧修复与经验沉淀。
- **根因（更正）**：
  1. **服务器侧确有一处真问题**：该域名**只有 80 的 server 块，缺 `listen 443` + 证书**（`nginx -t` 仍通过）。带 SNI 的 HTTPS 请求匹配不到本站 → 落到默认 443 站 → `curl: (35) Recv failure: Connection was reset`。已按部署教程 §9.4 补全 80 + 443 两块并 `reload nginx`。
  2. **"本机不可达"的另一半是假象**：本机（公司内网 `ad-main.intra.twdl.com` / `192.168.60.x`）存在透明代理/上网行为管理，对非白名单域名返回 `403`（响应头 **`Server: Beaver`**）或对 443 直接 reset。判定依据：① `Beaver` 不是 Nginx 的标识（Nginx 只会写 `Server: nginx`）；② 源站 `access.log` 全程**无 403** 且外部 IP 请求 `/` 拿到 301；③ 服务器本机 `-H Host` 测试返回 301；④ **手机 4G 打开 `/api/v1/health` 返回 `{"status":"ok"}`**。
- **变更摘要（文档为主，无业务代码改动）**：
  ① 【部署教程】新增 [§13.4 "域名/接口'网络异常'的分层排查（含内网假象）"](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md)：四层验证矩阵、`Server:` 头判据、`access.log` 佐证法、内网假象识别与正确验证姿势；
  ② 【部署教程】§8.1 修正"等于没换"的占位 sed（改用 `DOMAIN` 变量）并补 `grep -rn` **防重复 `server_name`**；
  ③ 【部署教程】§8.4 增补"**只有 80 块、缺 443+证书**"这一隐蔽坑，并强调"语法正确 ≠ 配置生效"（用 `nginx -T | grep -n -A3 域名` 复核）；
  ④ 【部署教程】§9.4 补"先 `certbot certificates` 查是否已签发、别重复签"；§10 补"体验版真机复测**必须用手机移动数据**、勿用公司内网 WiFi"；
  ⑤ 【部署教程】§13.1 / §13.3 表格各补若干行（reset / `Server: Beaver` / 内网假象 / 体验版网络异常 / 重复 `server_name`）。
  ⑥ 【排查文档】[体验版微信登录网络异常修复方案 §8.2](file:///d:/Users/weij/ai-error-learn/.trae/documents/体验版微信登录网络异常修复方案.md) **勘误更正**：由"服务器未配 443、阻塞"改为"内网假象 + 服务器 443 已补全、公网验证通过"。
  ⑦ 刷新根目录 `todo.md`。
- **影响模块**：
  - 文档：`.trae/documents/部署教程.md`（§8.1 / §8.4 / §9.4 / §10 / §13.1 / §13.3 / 新增 §13.4）、`.trae/documents/体验版微信登录网络异常修复方案.md`（§7 注记 + §8.2 勘误）、`.trae/docs/change-log.md`（本条）、`todo.md`
  - 服务器（运维动作，非代码）：`/etc/nginx/conf.d/error-learn.conf` 补全 443 块（含证书引用）
  - **未改动**：`client/**`、`server/**`、`deploy/**`、`.trae/specs/**`
- **关联文档路径**：`.trae/documents/体验版微信登录网络异常修复方案.md`、`.trae/documents/部署教程.md`
- **是否待合并主 spec**：**否**（文档/运维沉淀，未修改 `.trae/specs/mvp-reverse-docs/`）
- **验证结果**：
  - 服务器：`sudo nginx -t` → `syntax is ok` / `test is successful`；`ss -tlnp | grep :443` → 443 正在监听；`nginx -T | grep -A3 errorlearn` → 可见 `listen 443 ssl http2;` 与 `/etc/letsencrypt/live/errorlearn.diamondwtech.com/{fullchain,privkey}.pem`；`certbot certificates` → 该域名证书已签发（剩余 89 天）
  - 公网（**手机 4G**）：`https://errorlearn.diamondwtech.com/api/v1/health` → **`{"status":"ok"}`** ✅
  - 源站本机：`-H "Host: errorlearn.diamondwtech.com" http://127.0.0.1/` → **301**
- **待办（用户侧，阻塞体验版最终验收）**：mp 后台「服务器域名」配 `request`/`uploadFile`/`downloadFile` → 生产构建上传 → **选为体验版 → 手机 4G 真机复测登录**
- **回滚方式**：文档改动按 git 回滚即可；服务器侧如需回退，`sudo cp /etc/nginx/conf.d/error-learn.conf.bak /etc/nginx/conf.d/error-learn.conf && sudo nginx -t && sudo systemctl reload nginx`（改动前已备份）。本次**未改动任何业务代码**。

---

## fix-20261019-体验版登录 -101：改用 DigiCert 证书，规避 LE Gen-Y 链兼容性

- **编号**：fix-20261019-体验版登录-cronet证书链
- **日期**：2026-10-19
- **背景**：体验版真机（安卓 + iPhone）点「微信一键登录」报 `request:fail errcode:-101 cronet_error_code:-101 net::ERR_CONNECTION_RESET`。此前生产域名、白名单、nginx 443 均已修复，问题仍在。
- **排查过程（逐层排除）**：
  1. **构建产物正常**：`client/dist/common.js` 含 `https://errorlearn.diamondwtech.com`，局域网 IP `192.168.60.37` 出现 0 次。
  2. **服务端 TLS 正常**：`ssl_protocols TLSv1.2 TLSv1.3`、ECDHE-RSA GCM 套件齐全；本机 `openssl s_client -tls1_2` → `TLSv1.2` + `Verify return code: 0 (ok)`。
  3. **请求确实到达**：`error.log` 记录 `recv() failed (104) while SSL handshaking`（client 为手机 4G IP）；`access.log` 无记录，因握手未完成、HTTP 请求从未开始，属预期现象。
  4. **网络与中间盒排除**：同一手机、同一 IP，微信内置浏览器打开 `https://errorlearn.diamondwtech.com/api/v1/health` → `HTTP/2.0 200`；同一时刻小程序 cronet 握手被 RST。
  5. **证书链定位**：Let's Encrypt 于 2026-10-16 续期后落到 Gen-Y 链 `叶 → YR2 → Root YR（交叉签名）→ ISRG Root X1`。`Root YR` 生成于 2025-09-03，官方标注尚未进入各类信任库；微信文档要求「证书必须被系统信任，即根证书已被系统内置」。
- **根因**：小程序 `wx.request` 在 Android 7.0.10+ / iOS 8.0.3+ 统一使用 cronet（自带根证书库），不接受该 Gen-Y 链，在 TLS 握手阶段直接断开；微信内置浏览器走 WKWebView + 系统信任库，可经 ISRG Root X1 交叉签名路径验证，故同一时间访问正常。
- **变更摘要**：
  ① 服务器换发 DigiCert DV 证书（叶 → `Encryption Everywhere DV TLS CA - G2` → `DigiCert Global Root G2`），存放 `/etc/nginx/certs/errorlearn/{fullchain.pem,privkey.pem}`，权限 644/600；
  ② `/etc/nginx/conf.d/error-learn.conf` 第 15-16 行证书指向由 `/etc/letsencrypt/live/errorlearn.diamondwtech.com/` 改为上述新目录；
  ③ `.gitignore` 增加 `*.key`、`*.pem`、`.env.bak`、`*.env.bak`、`.tmp-*`，防止私钥与临时文件入库。
- **影响模块**：服务器 nginx（运维动作）、`.gitignore`、`todo.md`。`story.diamondwtech.com` 的证书与 certbot 续期**未改动**；小程序代码与 `dist` 未改动，域名未变，**无需重新构建或重新上传**。
- **关联文档路径**：`.trae/docs/change-log.md`（本条）、`todo.md`
- **是否待合并主 spec**：**否**
- **验证结果**：
  - `nginx -t` 通过，`systemctl reload nginx` 成功，服务 `active`；
  - 服务端 `openssl s_client`：TLS1.3 `TLS_AES_256_GCM_SHA384`、TLS1.2 `ECDHE-RSA-AES256-GCM-SHA384`，均 `Verify return code: 0 (ok)`，issuer 为 `DigiCert Encryption Everywhere DV TLS CA - G2`；
  - 证书有效期 `2026-10-19 → 2027-01-16`（**仅 90 天，需在到期前续期**）。
- **回滚方式**：`sudo cp /root/error-learn.conf.bak-2026-10-19-111059 /etc/nginx/conf.d/error-learn.conf && sudo nginx -t && sudo systemctl reload nginx`。
- **待办**：手机杀掉微信进程后用 4G 复测体验版登录；稳定运行后 `certbot delete --cert-name errorlearn.diamondwtech.com`（勿动 story）；2027-01-02 前完成新证书续期。

---
