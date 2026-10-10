# 添加 Python 后端启动命令（npm 脚本）方案

## 1. Summary（目标与范围）

在 `client/package.json` 的 `scripts` 中新增两个 npm 脚本，用一条命令即可启动 `server/` 下的 FastAPI 后端。脚本统一使用 `server/.venv` 虚拟环境中的 Python（`server/.venv/Scripts/python.exe`），不再依赖全局 `python`：

- `server`：从 `client/` 目录一键启动后端（先做依赖检查 → 进入 `server/` → 自动加载 `.env` → 启动 uvicorn）。
- `server:check`：仅做后端依赖检查（缺依赖时打印安装提示并退出码 1），可独立调用，也被 `server` 复用。

约束（已与用户确认）：

- **纯 `package.json` 脚本实现，不新增任何文件**。
- **仅面向 Windows**（npm 默认 script-shell 为 `cmd.exe`，脚本用 cmd 语法 + 内联 venv 的 `python.exe`）。
- **自动加载 `.env`**；**缺依赖时提示安装**（不自动安装）。

## 2. Current State Analysis（现状分析）

- 后端为 FastAPI 应用：[main.py](file:///d:/Users/weij/ai-error-learn/server/app/main.py#L1-L4) 文件头注释给出启动命令 `uvicorn app.main:app --host 0.0.0.0 --port 8000`，但**没有任何便捷脚本/命令**，需手动 cd 并输入长命令。
- 配置来源：[config.py](file:///d:/Users/weij/ai-error-learn/server/app/config.py#L49-L58) 只从 `os.environ` 读取 `ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET`、`OCR_ENDPOINT`、`OCR_MAX_IMAGE_BYTES`、`AI_ENABLED`；**不会自动加载 `.env`**。
- 环境变量样例：[.env.example](file:///d:/Users/weij/ai-error-learn/server/.env.example)；`.env` 已被 [.gitignore](file:///d:/Users/weij/ai-error-learn/.gitignore#L18-L20) 忽略，当前仓库**不存在 `.env`**。
- 依赖清单：[requirements.txt](file:///d:/Users/weij/ai-error-learn/server/requirements.txt) 含 `fastapi`、`uvicorn[standard]`、`python-multipart`、阿里云 OCR SDK（`alibabacloud_ocr_api20210707` / `alibabacloud_tea_openapi` / `alibabacloud_tea_util`）等。
- OCR SDK 在 [aliyun_ocr.py](file:///d:/Users/weij/ai-error-learn/server/app/services/aliyun_ocr.py#L104-L122) 中**延迟导入**（方法内 import），因此缺 SDK 时应用仍能启动、仅在真正调用 OCR 时报错；但作为后端完整依赖，检查脚本仍将其纳入。
- 前端 OCR 基址默认 `http://127.0.0.1:8000`（见开发计划 §Step 4），故后端固定监听 `8000` 端口。
- `client/package.json` 现有 `scripts` 均为 Taro 构建/监听命令（[package.json](file:///d:/Users/weij/ai-error-learn/client/package.json#L12-L31)），尚无后端相关脚本。
- 项目使用 pnpm（存在 `pnpm-lock.yaml`），脚本内容尽量与包管理器无关。

## 3. Proposed Changes（具体改动）

**唯一改动文件**：`client/package.json` —— 在 `scripts` 对象中新增两项（放在末尾，保持现有键不变）。

### 3.1 新增脚本 `server:check`（依赖检查）

作用：检查后端启动所需模块是否已安装；缺失则打印缺失项 + 安装提示并返回退出码 1（中断后续启动），全部具备则打印通过。

值（JSON 中需对双引号转义）：

```
..\server\.venv\Scripts\python.exe -c "import importlib.util as u,sys; miss=[m for m in ('fastapi','uvicorn','alibabacloud_ocr_api20210707') if u.find_spec(m) is None]; (print('缺少后端依赖: '+', '.join(miss)), print('请先执行: ../server/.venv/Scripts/python.exe -m pip install -r ../server/requirements.txt'), sys.exit(1)) if miss else print('后端依赖检查通过')"
```

说明：

- 用 `importlib.util.find_spec` 探测，避免真实导入 SDK 的副作用。
- `(…, …, sys.exit(1)) if miss else …` 为合法 Python 三元表达式（三元分支用**元组逗号**分隔语句，不能用分号）。
- 脚本代码内仅使用单引号，外层用双引号包裹，避免与 JSON/`cmd` 引号冲突。
- 用 venv 内的 Python（`..\server\.venv\Scripts\python.exe`）执行检查，与启动脚本使用同一解释器，避免“检查通过但启动用了另一个 Python”的偏差；`server:check` 的 cwd 为 `client/`，故路径带 `..\server\` 前缀。

### 3.2 新增脚本 `server`（一键启动）

值：

```
npm run server:check && cd ../server && (if exist .env (.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env) else (.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload))
```

说明：

1. `npm run server:check`：先跑依赖检查，失败即中断（`&&`）。
2. `cd ../server`：切换到后端目录，保证 `app.main:app` 可被导入（`pytest.ini` 的 `pythonpath=.` 亦印证后端以 `server/` 为工作目录）。
3. `if exist .env (...) else (...)`：**仅当 `.env` 存在时才加 `--env-file .env`**，避免文件缺失导致 uvicorn 报错；`--env-file` 由 uvicorn(>=0.21，本项目 `>=0.29`) 原生支持，会加载 `.env` 到进程环境变量，被 `config.py` 读取。
4. `.venv\Scripts\python.exe -m uvicorn ...`：用 venv 内的 Python 以模块方式调用，既避免与全局解释器的依赖不一致，也避免 `uvicorn` 未在 PATH 的问题（`cd ../server` 后即 `server/` 下相对路径）。
5. `--reload`：开发期热重载（`uvicorn[standard]` 已含 watchfiles）。
6. 端口 `8000`/host `0.0.0.0`：与 [main.py](file:///d:/Users/weij/ai-error-learn/server/app/main.py#L3) 注释及前端默认基址一致。

### 3.3 改动后的 scripts 片段（示意）

```json
"scripts": {
  "build:weapp": "taro build --type weapp",
  "...": "（其余键保持不变）",
  "server:check": "..\\server\\.venv\\Scripts\\python.exe -c \"...\"",
  "server": "npm run server:check && cd ../server && (if exist .env (.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --env-file .env) else (.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload))"
}
```

## 4. Assumptions & Decisions（假设与决策）

1. **Windows + npm 默认 cmd.exe**：用户已选“纯 package.json（Windows 专用）”，脚本采用 cmd 语法（`if exist`、`&&`、括号分组）。若用户把 npm `script-shell` 改成 PowerShell，需另行调整。
2. **使用 venv 内的 Python**：脚本统一调用 `server/.venv/Scripts/python.exe`（`server:check` 因 cwd 为 `client/` 而写 `..\server\.venv\Scripts\python.exe`），依赖装在 `server/.venv` 中，不再使用全局 `python`。
3. **`.env` 缺失时的行为**：不自动创建 `.env`，改为不带 `--env-file` 启动；此时密钥为空，OCR 调用会按设计报错（`config.py` 已保证缺失密钥不崩溃）。仅给出安装/配置提示逻辑，不落盘任何文件。
4. **依赖检查范围**：`fastapi`、`uvicorn`、`alibabacloud_ocr_api20210707`（后端完整运行所需）；不检查测试专用依赖（`pytest`/`httpx`）。
5. **不自动安装依赖**：仅在缺失时提示 `../server/.venv/Scripts/python.exe -m pip install -r ../server/requirements.txt`，由用户自行执行。
6. **端口固定 8000**：不改造成可配置（用户未要求，避免过度设计）。
7. **仅改 `package.json`**：不新增 `run.py`/`.bat` 等文件，不改后端源码。
8. **前置条件：`server/.venv` 已存在且已装依赖**：首次使用需先 `python -m venv server/.venv` 并执行 `server/.venv/Scripts/python.exe -m pip install -r server/requirements.txt`；`server:check` 即基于该解释器检查。

## 5. Verification（验收步骤）

在 `client/` 目录下执行：

1. **依赖检查成功路径**：已安装依赖时运行 `npm run server:check`（或 `pnpm run server:check`）→ 输出 `后端依赖检查通过`，退出码 0。
2. **依赖检查失败路径**（可选，在删除或新建空 venv 后验证）：输出 `缺少后端依赖: ...` 与 `请先执行: ../server/.venv/Scripts/python.exe -m pip install -r ../server/requirements.txt`，且后续启动被中断。
3. **启动**：`npm run server` → uvicorn 成功监听 `http://0.0.0.0:8000`；日志显示启动完成。
4. **健康检查**：浏览器/终端访问 `http://127.0.0.1:8000/api/v1/health` → 返回 `{"status":"ok"}`。
5. **.env 生效验证**：在 `server/.env` 写入 `OCR_ENDPOINT=...` 后启动，确认 `config.py` 读取到该值（例如通过一次 OCR 调用观察使用端点，或临时日志；无 `.env` 时启动不报错）。
6. **热重载**：修改 `server/app/main.py` 后 uvicorn 自动重启。
7. `GetDiagnostics` 确认 `package.json` 无 JSON 语法错误。
