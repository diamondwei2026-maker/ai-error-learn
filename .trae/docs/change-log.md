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
