# 更新部署教程 —— 阿里云共享 ECS 场景

> 状态：待确认　｜　创建日期：2026-10-15
> 目标产物：[`.trae/documents/部署教程.md`](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md)

---

## 1. 摘要（Summary）

把现有《部署教程》从"全新服务器"口径，改写为**以用户真实环境为主线**的教程：

- **ECS 已有原生 Nginx 与其它站点**，且 80/443 已被占用；
- **数据库为阿里云 RDS 独立实例**（非复用既有库）；
- **域名有已备案主域名，但需新开子域名**并单独申请证书。

改造的核心原则：**全程不触碰既有站点配置**，本项目以"新增一个独立 `server_name` 子域名的 Nginx 配置文件 + 独立 systemd 服务"的方式共存；任何一步都可**独立回滚**。

---

## 2. 现状分析（Current State Analysis）

### 2.1 现有教程的问题（实测）

| 位置 | 现状 | 问题 |
| --- | --- | --- |
| [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L9-L17) 第 0 章 | 「前置三件事」按全新服务器表述 | 未体现"已有站点/已有 Nginx 环境"这一前提 |
| [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L195-L203) §3.3 | 共存内容被压缩为 5 条脚注 | 用户的主线场景被当成边缘情况，缺少可执行步骤与回滚 |
| [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L64-L73) §2.2 | `apt install nginx` 与 `pip` 安装 | 共享服务器上**不应重装 Nginx**，需改为"只补 Python 依赖，不动 Nginx 安装" |
| [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L132-L165) §3.1 | 证书三方案并列 | 因 80 被现有站点占用，**DNS-01 应是唯一主推**，HTTP-01 明确不可用 |
| [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md#L99-L99) §2.3 | RDS 表述为"复用/新建"混合 | 需明确为**独立 RDS 实例**的第二条链路 |

### 2.2 部署产物现状（实测）

| 文件 | 关键事实 |
| --- | --- |
| [error-learn.conf](file:///d:/Users/weij/ai-error-learn/deploy/nginx/error-learn.conf) | 独立 server 块、3 处占位、`proxy_pass 127.0.0.1:8000`（出现 2 处）、`/static/` alias、`http2` 版本分支注释 —— **结构已适配共存**，可直接复用 |
| [error-learn-api.service](file:///d:/Users/weij/ai-error-learn/deploy/systemd/error-learn-api.service) | `<DEPLOY_DIR>` 占位、`--port 8000` 硬编码、`User=www-data` 可替换 |
| [deploy.sh](file:///d:/Users/weij/ai-error-learn/deploy/deploy.sh) | 已做 `nginx -t` + `reload`（不 restart）、`<DEPLOY_DIR>` 替换；**缺** 端口占用预检、**缺** 端口可配置 |
| [env.production.example](file:///d:/Users/weij/ai-error-learn/deploy/env.production.example) | 已含 `UPLOADS_DIR` / RDS 连接串模板 —— 无需改动 |

### 2.3 代码侧事实（与教程必须一致，实测）

- 健康检查 `GET /api/v1/health` → `{"status":"ok"}`（[main.py](file:///d:/Users/weij/ai-error-learn/server/app/main.py#L92-L94)）
- 静态挂载 `/static` → `UPLOADS_DIR`（[config.py](file:///d:/Users/weij/ai-error-learn/server/app/config.py#L151-L151) 读 `UPLOADS_DIR`）
- 后端端口 `8000` 仅出现在 systemd / nginx 模板中，**应用本身未硬编码端口**，可安全改
- 前端基址由 `TARO_APP_API_BASE` 注入（[constants/index.ts](file:///d:/Users/weij/ai-error-learn/client/src/constants/index.ts#L30-L30)）
- MySQL 8 需 `PyMySQL[rsa]`（cryptography）—— 独立 RDS 同样是 MySQL 8，结论不变

---

## 3. 方案（Proposed Changes）

### 3.1 核心产物：重写 [`部署教程.md`](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md)

**新结构（按执行顺序，决策已完成）：**

| 章节 | 内容要点 |
| --- | --- |
| **0. 场景与前提** | 明确三条前提：① ECS 已有原生 Nginx + 站点；② 独立 RDS 实例；③ 有备案主域名、需新开子域名。给出"本次只新增、不改动既有站点"的承诺 |
| **1. 目标架构** | 保留现有架构图，**新增**共存视角：现有站点 `server_name a.com` 与新增 `api.a.com` 共用同一 Nginx，SNI/`server_name` 分流，互不影响 |
| **2. 前置准备** | ① 子域名规划（建议 `api.<主域名>`，须在主域名备案范围内）；② 独立 RDS 实例已创建；③ 小程序备案；④ ECS 安全组放行 443（80 可选）；⑤ RDS 白名单 |
| **3. 现状勘察（新增）** | 在已有服务器上先摸底，命令逐条给出并解释看什么：`nginx -v`、`nginx -T \| grep server_name`、`ls /etc/nginx/conf.d/`、`ss -lntp \| grep -E ':(80\|443\|8000)'`、`ps -o user= -C nginx`、`ls ~/.acme.sh` / `which certbot`、`free -m`。**产出结论**：Nginx 版本（决定 `http2` 写法）、运行用户、8000 是否被占、是否已有 acme.sh |
| **4. 后端部署** | 改为"**只补 Python 依赖，不重装 Nginx**"；若 8000 被占 → 改用备用端口（如 `8080`）并全文同步；venv、`.env`（独立 RDS 连接串）、systemd 安装；本机 health 自检 |
| **5. 接入现有 Nginx（新增，替代旧 §3.2）** | 新增文件 `/etc/nginx/conf.d/error-learn.conf`（**不修改任何既有文件**）；子域名与证书 3 处占位替换；`nginx -t` → `reload`；**明确"只 reload 不 restart"及其原因**；给出**回滚 = 删文件 + reload** |
| **6. 申请证书（改写旧 §3.1）** | 因 80 被现有站点占用，**DNS-01（阿里云 DNS API）为唯一主推**；明确写"HTTP-01 不可用"；acme.sh 四步 + `--install-cert` 自动续签；备选：阿里云控制台证书（90 天人工轮换） |
| **7. 前端构建发布** | 沿用，补"构建机可为本地开发机，不必在 ECS" |
| **8. 微信平台配置** | 沿用（合法域名 ×3、隐私指引），域名替换为新子域名 |
| **9. 运维** | 新增「**与现有站点互不影响的更新流程**」；证书巡检；备份（独立 RDS 控制台） |
| **10. 排障** | 旧表格保留，**新增**共享环境专属项：Nginx 配置冲突/`nginx -t` 失败、端口占用、权限（`www-data`）、SNI 访不到新子域名、`403/404` 排查 |
| **11. 影响范围与回滚（新增）** | 一张表列"新增了什么 / 动了什么（唯一 `reload`）/ 如何回滚"，消除用户对生产服务器的顾虑 |
| **参考来源** | 保留并补阿里云云解析（DNS-01）、ECS 安全组条目 |

**关键决策（已定，执行者无需再选）：**

1. 子域名命名统一用 `api.example.com` 作为占位（沿用现有占位，避免引入新占位符）。
2. 证书方案**只主推 DNS-01**，HTTP-01 在共享 80 场景写明"不可用"。
3. 后端端口默认 `8000`；若勘察发现被占，**统一改为 `8080`**（文档给判断条件与替换点清单）。
4. Nginx 配置文件命名固定 `error-learn.conf`（`conf.d/` 下，与既有站点文件并列，删除即回滚）。
5. 运行用户以**勘察结论为准**（`www-data` 或 `nginx`），文档给出取用户命令而非猜。

### 3.2 配套：让 [`deploy.sh`](file:///d:/Users/weij/ai-error-learn/deploy/deploy.sh) 支持共享服务器

> 理由：共享服务器上 8000 可能被占；且需在动手前就拦下端口冲突，而不是装完 systemd 才失败。改动**保持最小**。

| 改动点 | 具体做法 |
| --- | --- |
| 新增 `PORT` 变量 | `PORT="${PORT:-8000}"`，与 `DEPLOY_DIR` 同级别 |
| 新增端口预检 | 在 `check_prereq` 中：`ss -lnt \| grep -q ":${PORT} "` → 若被占则 `die` 并提示"用 PORT=8080 重跑"，**不自动改端口** |
| systemd 端口替换 | `setup_systemd` 的 sed 增加 `s#--port 8000#--port ${PORT}#` |
| nginx 端口替换 | `setup_nginx` 的 sed 增加 `s#127.0.0.1:8000#127.0.0.1:${PORT}#g`（覆盖 `proxy_pass` 与 `/health` 两处） |
| 健康检查 | `health_check` 中 `127.0.0.1:8000` 改为 `127.0.0.1:${PORT}` |
| 头部注释 | 用法区补 `PORT` 示例，并注明"共享服务器只 reload 不 restart" |

**不改**：`error-learn.conf` 与 `error-learn-api.service` 模板本身（端口靠 sed 替换，保持模板可读）。

### 3.3 配套：变更索引

- 在 [change-log.md](file:///d:/Users/weij/ai-error-learn/.trae/docs/change-log.md) 追加一条 `docs-20261015-部署教程共享ECS改写`，字段按现有格式（编号/日期/摘要/影响模块/关联文档/是否待合并主 spec/验证/回滚）。

---

## 4. 假设与决策（Assumptions & Decisions）

| # | 假设 / 决策 | 依据 |
| --- | --- | --- |
| A1 | ECS 上**已有可用 Nginx**，因此部署**不重装 Nginx**，只补 Python 依赖 | 用户确认"原生 Nginx，已有站点" |
| A2 | 新增站点用**独立 `server_name` 子域名**接入，靠 SNI 与既有站点分流，不改动既有配置文件 | 8000/80/443 已被占，且 ECS 只有一块 443 |
| A3 | 证书走 **DNS-01**（阿里云 DNS API），因 HTTP-01 需 80 端口而 80 已被现有站点占用 | 用户场景 + acme.sh 能力 |
| A4 | 数据库为**独立 RDS 实例**，需新建库 `error_learn` 并把 ECS 内网 IP 加入该实例白名单 | 用户确认"另一个独立 RDS 实例" |
| A5 | 子域名须落在**已备案主域名**范围内，无需额外备案（主域名已备案） | 用户确认"有备案主域名" |
| A6 | 后端端口默认 8000，冲突时统一改 8080 | 8000 非特权端口，改动仅涉及模板 sed |
| A7 | **不涉及前端页面/PII 变更**，故**不触发原型流程**（工作流规则第 2 条仅约束"页面类前端需求"） | 本次为文档 + 部署脚本 |
| A8 | 教程保持**纯操作手册**口径，不写现状分析/风险长文（与既有约定一致） | 现有教程定位 |

---

## 5. 验证（Verification）

执行完成后逐项核对：

1. **文档自洽**：教程中出现的每个端口、路径、URL，与 `deploy/**`、`server/app/main.py`、`config.py` 实际一致（人工逐条比对）。
2. **脚本语法**：`bash -n deploy/deploy.sh`（在 Git Bash / WSL 或 ECS 上）→ 无语法错误。
3. **端口替换逻辑**：`PORT=8080` 时，生成的 systemd 与 nginx 配置中 `8000` 应被完全替换（可用 `sed` 预演输出比对，不落盘）。
4. **不触碰既有站点**：确认 `deploy.sh` 全文**无 `nginx restart`**、**无修改既有 conf 文件**、**无重装 nginx**。
5. **回滚可执行**：按教程 §11 的回滚步骤（删 `error-learn.conf` + `systemctl reload nginx` + `systemctl disable --now error-learn-api`），确认每一步都有对应命令。
6. **变更索引**：`change-log.md` 新条目字段完整。

---

## 6. 交付清单

| 文件 | 动作 |
| --- | --- |
| [.trae/documents/部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md) | **重写**（按 §3.1 新结构） |
| [deploy/deploy.sh](file:///d:/Users/weij/ai-error-learn/deploy/deploy.sh) | 修改（按 §3.2，新增 PORT + 端口预检 + 端口替换） |
| [.trae/docs/change-log.md](file:///d:/Users/weij/ai-error-learn/.trae/docs/change-log.md) | 追加变更记录 |
| `deploy/nginx/error-learn.conf`、`deploy/systemd/*.service`、`env.production.example` | **不改** |
| 前端代码 / 后端代码 | **不改** |
