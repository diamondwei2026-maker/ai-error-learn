# 后端服务启动失败（[WinError 10013]）修复方案

> 性质：**方案文档（未改动任何代码/配置/进程）**，确认后按项目规则执行
> 触发问题：启动 Python 后端时报
> `ERROR:    [WinError 10013] 以一种访问权限不允许的方式做了一个访问套接字的尝试。`
> 排查日期：2026-10-16
> 关联前案：[开发环境网络异常排查与修复方案.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/开发环境网络异常排查与修复方案.md)（同一天，遗留进程问题的上一次处置）

---

## 1. 摘要（结论先行）

**根因：8000 端口已被一个**遗留的 uvicorn 实例**占用（PID 316 / 13208，启动于今天 16:03:57），新实例无法绑定该端口；由于 uvicorn 在 Windows 上会给监听 socket 设置 `SO_REUSEADDR`，Windows 把这次「端口冲突」报成了 `WSAEACCES`（WinError 10013），而不是更常见的 `10048（地址已使用）`** —— 这是本次报错「看起来像权限问题、其实是用端口被占」的原因。

**处置结论（已与用户确认）**：停掉遗留实例 → 校验端口释放 → 用 `npm run server` 干净启动**单实例**（带 `--reload`，便于后续热重载）；**不加**防复发脚本，不改任何仓库文件（与上一次 `fix-20261016` 的处置口径一致）。

### 根因证据链（均为本机实测）

| # | 证据 | 实测结果 |
| --- | --- | --- |
| 1 | 8000 端口当前监听者 | `Get-NetTCPConnection -LocalPort 8000` → `0.0.0.0:8000  Listen  PID 13208`（**已被占用**） |
| 2 | 占用者身份 | PID 316 = `server\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env`；PID 13208 = 其子进程 `D:\python3.12\python.exe`（Windows 下 venv 的 `python.exe` 是启动器，会再拉起基础解释器，**父/子两个进程都要停**）；两者启动时间均为 `2026/10/16 16:03:57` |
| 3 | 该实例是否「旧代码」 | 否。`GET /api/v1/health` → `200 {"status":"ok"}`；`/openapi.json` 已含 `/api/v1/security/text-check`、`/api/v1/wechat/callback` → **跑的是最新代码，实例本身健康** |
| 4 | 复现「10013 vs 10048」 | 用 `server\.venv` 的 Python 实测：对已被占用的 `0.0.0.0:8123` 二次 bind —— **不带** `SO_REUSEADDR` → `errno 10048`；**带** `SO_REUSEADDR` → `errno 13` 且 `strerror` 正是「以一种访问权限不允许的方式做了一个访问套接字的尝试。」 |
| 5 | 代码依据 | `uvicorn 0.54.0` 的 [config.py L600-606](file:///d:/Users/weij/ai-error-learn/server/.venv/Lib/site-packages/uvicorn/config.py#L600-L606)：`sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)` → `sock.bind(...)` → `except OSError: logger.error(exc); sys.exit(STARTUP_FAILURE)`，因此报错文案形如 `ERROR:    [WinError 10013] ...` |
| 6 | 已排除项①：Hyper-V / WinNAT 保留端口段 | `netsh interface ipv4 show excludedportrange protocol=tcp` → 仅 `5357-5357`；`winnat` 服务 `Stopped` → **不是**保留端口段导致 |
| 7 | 已排除项②：host/端口写错 | 启动命令与 [main.py L3](file:///d:/Users/weij/ai-error-learn/server/app/main.py#L3) 注释、[package.json L32](file:///d:/Users/weij/ai-error-learn/client/package.json#L32) 脚本、[client/.env.development](file:///d:/Users/weij/ai-error-learn/client/.env.development) 的 `http://192.168.60.37:8000` 完全一致 |
| 8 | 已排除项③：环境/配置非法导致起不来 | `server/.env` 上次已修正：`DATABASE_URL=sqlite:///./app.db`、`CONTENT_SECURITY_ENABLED=false`，且当前实例能用这份 `.env` 正常启动 → **本次报错与配置无关** |

### 影响面

- 仅本机开发环境的**进程/端口**问题：**不涉及任何代码、配置、数据库变更**。
- 后端对前端的可用性：当前 8000 上其实**已有一个健康实例在跑**，所以「启动失败」不影响此刻联调；但如果继续在别的终端重启，就会稳定复现 10013。

---

## 2. 现状分析

1. **端口占用是唯一失败点**：uvicorn 启动流程是「先 bind 端口，再加载应用」，bind 失败即 `sys.exit(STARTUP_FAILURE)`，报错发生在导入 `app.main` 之前 → 与「日志里只有一行 WinError 10013、看不到任何应用启动日志」的现象吻合。
2. **为什么是 10013 而不是 10048**：Windows 的 `SO_REUSEADDR` 语义与 Linux 不同。端口已被他人正常绑定时，二次绑定**带** `SO_REUSEADDR` 会被拒为 `WSAEACCES(10013)`；不带才是 `WSAEADDRINUSE(10048)`。uvicorn 恰恰带了该选项（证据 4/5），所以「端口被占」被包装成了「权限不足」，这是本次排查容易跑偏的关键。
3. **遗留实例的来源**：进程命令行显示它是被「一次工具化启动」拉起的（`--env-file .env`、无 `--reload`），即上一次会话为验收而启动的实例被保留至今，未随会话结束回收 → 属于**重复出现三次的同类问题**（10/14、10/15、10/16）。
4. **本次不改仓库文件**：用户已明确选择「不加防复发预检」，因此不动 [package.json](file:///d:/Users/weij/ai-error-learn/client/package.json)；`server/.env` 也已在上一次修复中处于正确状态，本次**不改**。

---

## 3. 修复方案（按顺序执行）

> 执行原则：PID 一律**执行时重新探测**，不硬编码（避免与上面表格中的瞬时 PID 不一致）。

### 步骤 0：刷新根目录会话任务清单（用户规则）

更新 [todo.md](file:///d:/Users/weij/ai-error-learn/todo.md)：置为本次「后端启动失败（WinError 10013）修复」的任务清单，列清任务总数与逐项状态。

### 步骤 1：确认 8000 端口占用者

```powershell
netstat -ano | Select-String ":8000"
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*uvicorn app.main:app*' } |
  Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine
```

判定：若 `0.0.0.0:8000` 处于 `Listen` 且 OwningProcess 为 python/uvicorn → 命中本方案；**若端口已空闲** → 跳过步骤 2，并直接采用 §6 的备选排查清单。

### 步骤 2：停止遗留实例（父/子进程一起停）

对步骤 1 得到的**监听进程**与其**父进程**（venv 启动器）分别执行：

```powershell
Stop-Process -Id <监听进程PID> -Force    # 例：13208（真正 listen 的那个）
Stop-Process -Id <父进程PID> -Force      # 例：316（venv Scripts\python.exe）
```

说明：只停子进程时，父进程可能残留并在端口释放后重建监听，故必须成对停；两个 PID 都取自步骤 1 的实测输出。

### 步骤 3：校验端口已释放

```powershell
netstat -ano | Select-String ":8000"   # 期望：无输出
cd d:\Users\weij\ai-error-learn\server
.\.venv\Scripts\python.exe -c "import socket; s=socket.socket(); s.bind(('0.0.0.0',8000)); print('8000 FREE'); s.close()"
# 期望：打印 8000 FREE；若报 10048/10013 → 说明仍有占用或存在保留端口段，转 §6
```

### 步骤 4：干净启动单实例

在 `client/` 目录执行（复用现有脚本：**依赖检查 → 加载 `.env` → `--reload` 热重载**）：

```powershell
cd d:\Users\weij\ai-error-learn\client
npm run server
```

等价直连命令（当 npm 脚本异常时的备选）：

```powershell
cd d:\Users\weij\ai-error-learn\server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env
```

- 以**常驻后台**方式运行（非阻塞），保留日志输出供步骤 5 验收。
- 该实例将被保留为开发期唯一后端；后续改后端代码由 `--reload` 自动重启（这正是相对遗留实例的改进点）。

### 步骤 5：验收（必须全部满足）

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health -UseBasicParsing | Select-Object StatusCode,Content
(Invoke-WebRequest http://127.0.0.1:8000/openapi.json -UseBasicParsing).Content | ConvertFrom-Json | ForEach-Object { $_.paths.PSObject.Properties.Name }
Get-NetTCPConnection -LocalPort 8000 | Select-Object LocalAddress,State,OwningProcess
```

| 验收点 | 期望 |
| --- | --- |
| 启动日志 | **无** `[WinError 10013]`、无 `[Errno 10048]`，出现 `Application startup complete` |
| 健康检查 | `200 {"status":"ok"}` |
| 路由完整性 | `/openapi.json` 含 `/api/v1/security/text-check`、`/api/v1/wechat/callback` |
| 端口归属 | 8000 上**仅 1 个** LISTENING 进程（本次新起的那个），无父子双实例残留 |
| 依赖检查 | `npm run server` 首行输出 `后端依赖检查通过` |

### 步骤 6：收尾（文档与变更记录）

1. 在 [change-log.md](file:///d:/Users/weij/ai-error-learn/.trae/docs/change-log.md) 末尾追加一条：
   - 编号：`fix-20261016-后端启动端口占用(WinError 10013)修复`
   - 日期、背景（本次报错 + 根因：遗留实例占用 8000，uvicorn 的 `SO_REUSEADDR` 使冲突表现为 10013）
   - 变更摘要（停遗留进程 → 干净重启单实例；**零代码/配置改动**）
   - 影响模块、关联文档路径（本方案文档）、是否待合并主 spec（**否**）、验证结果、回滚方式
2. 更新 [todo.md](file:///d:/Users/weij/ai-error-learn/todo.md) 全部任务为已完成。
3. 输出变更摘要（改动文件清单 + 验收结论 + 你后续需要注意的点）。

---

## 4. 假设与决策

| # | 决策 | 依据 |
| --- | --- | --- |
| 1 | **停掉遗留实例、干净重启单实例**（而非保留在跑的健康实例） | 用户已确认；重启后实例带 `--reload`，后续改后端代码无需手动重启 |
| 2 | **不加防复发措施**（不改 `client/package.json` 的端口预检） | 用户已确认；本次只做环境修复 |
| 3 | **不改任何仓库文件与 `server/.env`** | 报错根因是端口占用；`.env` 在上次修复后已正确（`sqlite:///./app.db`），无证据表明需要再改 |
| 4 | **端口仍固定 8000** | 与 `client/.env.development` 的 `TARO_APP_API_BASE=http://192.168.60.37:8000`、deploy 配置一致；换端口会牵连前端与部署配置，不在本次范围 |
| 5 | **执行时重新探测 PID** | 进程表随会话变化，硬编码 PID 会导致误杀 |
| 6 | **不触发原型流程** | 环境/进程修复，无新增页面、无 UI 结构/视觉与业务逻辑改动 |

---

## 5. 影响范围与回滚

| 项 | 影响 | 回滚 |
| --- | --- | --- |
| 停止 PID（遗留 uvicorn） | 8000 端口短暂不可用（数秒） | 重新执行原启动命令即可恢复 |
| 新起单实例（`npm run server`） | 开发期后端常驻，带热重载 | `Ctrl+C`／停止该进程 |
| 仓库代码 / `server/.env` / `client/package.json` | **本次均不修改** | — |
| 追加的文档与 change-log | 仅文档 | 删除对应段落 |

---

## 6. 备选排查清单（仅当「端口已空闲后仍报 10013」时按序启用）

| 序 | 检查 | 命令 / 处置 |
| --- | --- | --- |
| 1 | 是否有保留/排除端口段（Hyper-V、WinNAT、WSL、Docker） | `netsh interface ipv4 show excludedportrange protocol=tcp`；`Get-Service winnat`。本次实测仅 `5357` 且 `winnat` 已 Stopped → 已排除；若命中，可 `net stop winnat` 后启动再 `net start winnat`，或用 `netsh int ipv4 delete excludedportrange` 释放 |
| 2 | 是否有安全软件/防火墙拦截监听 | 临时退出/放行（如 360、火绒）；或用管理员 PowerShell 复测一次 |
| 3 | 端口被其它类型程序占用（非 python） | `Get-Process -Id <OwningProcess>` 确认归属，再决定是否停用 |
| 4 | 以上都不成立 | 换端口启动（`--port 8001`），并同步 `client/.env.development` 的 `TARO_APP_API_BASE`；这属于新的方案变更，会**先出方案再改** |

---

## 7. 备注（与本次报错无关、但需留意的开发前置）

- `client/project.config.json` 的 `setting.urlCheck` 若为 `true`，微信开发者工具会校验合法域名；用 IP + HTTP 联调时需在「详情 → 本地设置」勾选「不校验合法域名…」并清缓存重编译（详见上一次修复方案的「待用户侧操作」）。
- 后端启动成功 ≠ 登录可用：若微信登录仍返回 `code 2004`，需核对 MP 后台 `WECHAT_APP_SECRET` 是否属于 AppID `wxf7fbaf8d9a6f7296`。
