# 生产识别失败修复（切换 GLM-4V-Flash + 同步可诊断代码）

## 0. 直接回答你的问题

| 疑问 | 结论（均已实测） |
| --- | --- |
| 是不是 `AI_ENABLED=false` 导致？ | **不是**。`AI_ENABLED` 只在 [config.py](file:///d:/Users/weij/ai-error-learn/server/app/config.py#L44) 解析为 `ai_enabled`，全仓库**从未被任何业务逻辑引用**；识别只受 `VISION_ENABLED / VISION_*` 控制。 |
| 是不是没钱了？ | **不是**。生产机器上用现有 Key 实测 `qwen3-vl-plus` 返回 **200**（0.6s），用 GLM 返回 **200**（0.6s）。当前真实报错是 `404 Model not exist`，不是余额/欠费。 |
| 我用的模型是什么？ | **本地/生产当前不一致**：<br>· 本地 `server/.env`：`glm-4v-flash` @ `https://open.bigmodel.cn/api/paas/v4`（实测 2.7s 可用）<br>· 生产 `/opt/error-learn/server/.env`：`qwen-vl-flash` @ `https://maas.qianwenaiapi.com/compatible-mode/v1`（**无效模型**） |
| 模型访问地址是什么？ | 本地：`https://open.bigmodel.cn/api/paas/v4`（智谱官方）<br>生产当前：`https://maas.qianwenaiapi.com/compatible-mode/v1`（第三方代理）<br>修复后生产：改为智谱官方地址 |
| 为什么真机和体验版都不行？ | 「体验版」走生产域名，命中了上面的 404；「真机 dev 预览」走本地局域网 `192.168.60.37:8000`，但**本地 8000 端口当前未监听**（后端没启动），因此也失败。 |

生产 404 实测原文：

```json
{"error":{"message":"Model not exist.","code":"model_not_found","type":"invalid_request_error"}}
```

该代理的 `GET /models` 共 182 个模型，视觉类只有：`qwen3-vl-plus`、`qwen-vl-ocr`、`qwen-vl-ocr-2025-11-20`；**不存在 `qwen-vl-flash` / `qwen3-vl-flash` / `qwen-vl-plus` / `qwen-vl-max`**。

## 1. Summary

按你的选择执行：

1. 生产模型切到**免费**的 `glm-4v-flash`（智谱官方地址，已实测生产服务器可直连且返回 200）。
2. 把上一轮的后端可诊断代码（错误细分 + 上游日志 + 启动配置日志）同步到生产并重启。
3. 本地真机联调失败按“后端未启动”处理，给出启动与联调检查项。

## 2. Current State Analysis

- 生产服务器：`root@47.96.160.201`，服务 `error-learn-api`，部署路径 `/opt/error-learn/server`，**非 git 仓库**（无 remote/无提交），代码时间戳 `2026-10-15 19:32`，不包含上一轮的日志/映射改动（`grep 'vision upstream'` 计数为 0）。
- 生产 `config.py` 已含 `vision_configured` 属性（line 65），因此只同步 `vision_recognize.py` 与 `main.py` 即可，不会因缺属性启动失败；服务器 venv 已安装 `httpx 0.28.1`。
- 生产 `.env` 关键项（Key 已脱敏）：`VISION_ENABLED=true`、`VISION_BASE_URL=https://maas.qianwenaiapi.com/compatible-mode/v1`、`VISION_MODEL=qwen-vl-flash`、`VISION_TIMEOUT=20`、`AI_ENABLED=false`。
- 本轮远程实测（只读探针，均从生产服务器发起）：
  - `qwen-vl-flash` → 404 `Model not exist.`
  - `qwen3-vl-flash` / `qwen-vl-plus` / `qwen-vl-max` → 404
  - `qwen3-vl-plus` → 200（64×64 PNG，0.6s）
  - `glm-4v-flash` @ 智谱官方 → 200（0.6s）
- 本地：`8000` 未监听；`glm-4v-flash` 直调与 `VisionClient.recognize` 均正常（约 2.7s）。
- 上一轮已改但**未部署**的文件：`server/app/services/vision_recognize.py`、`server/app/main.py`（客户端 `recognitionService.ts` 仅日志/文案，需重新构建小程序才生效，本次不强制）。

## 3. Proposed Changes

### 3.1 生产配置切换到免费 GLM（核心修复）

在 `47.96.160.201` 上执行：

1. 备份：`cp /opt/error-learn/server/.env /opt/error-learn/server/.env.bak-20261110`
2. 修改三行（保持其余不变）：
   - `VISION_BASE_URL=https://open.bigmodel.cn/api/paas/v4`
   - `VISION_API_KEY=<与本地 server/.env 相同的智谱 Key>`
   - `VISION_MODEL=glm-4v-flash`
3. `systemctl restart error-learn-api`，`systemctl is-active error-learn-api` 应为 `active`。

**为什么用这个 Key**：已在生产机器上实测该 Key + 官方地址 + `glm-4v-flash` 返回 200；模型免费，可直接消除费用顾虑。

### 3.2 同步可诊断代码（保留上一轮成果）

1. 远端备份：`vision_recognize.py`、`main.py` 各复制为 `*.bak-20261110`。
2. `scp` 覆盖两个文件到 `/opt/error-learn/server/app/...`。
3. `systemctl restart error-learn-api`；`journalctl -u error-learn-api -n 30 --no-pager` 应出现：
   `视觉模型：base=https://open.bigmodel.cn/api/paas/v4 model=glm-4v-flash timeout=20s`
4. 若启动失败：立即用 `.bak-20261110` 还原两个文件并重启（回滚）。

### 3.3 文档与记录

- [deploy/env.production.example](file:///d:/Users/weij/ai-error-learn/deploy/env.production.example)：在视觉模型段补充“第三方代理的模型目录各不相同，上线前用 `GET /models` 核对；本代理可用 `qwen3-vl-plus`；免费方案为智谱 `glm-4v-flash`”。
- [部署教程.md](file:///d:/Users/weij/ai-error-learn/.trae/documents/部署教程.md) A-7：补一段“若走第三方代理，先确认模型 ID 是否存在；否则上游 404 会被兜底成『识别失败』”。
- `.trae/docs/change-log.md` 追加本次修复记录；更新 `.trae/todolist/` 会话任务文件。

### 3.4 本地真机联调检查项（不改代码）

1. 先启动后端：仓库根目录 `npm run server`，确认 `http://192.168.60.37:8000/api/v1/health` 返回 `{"status":"ok"}`。
2. 手机与电脑同一 WiFi；开发者工具「详情 → 本地设置」勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。
3. `client/.env.development` 的 `TARO_APP_API_BASE` 保持局域网地址，重新编译后真机预览。

## 4. Assumptions & Decisions

1. 生产继续使用与本地相同的智谱 Key（已实测可用、模型免费）；不引入新账号。
2. `qwen3-vl-plus` 已验证可用但不采用，避免按量费用；若后续对复杂题目识别效果不满意，可仅改 `.env` 三行切回。
3. 不做自动重试/多模型降级；错误已在 3.2 后可在 `journalctl` 直接看到上游 status/body。
4. `AI_ENABLED` 保持 `false` 不动——它与识别无关。
5. 客户端文案改动需重新构建上传才生效，本次不阻塞识别恢复，不强制重新上传体验版。

## 5. Verification

1. 生产远端探针：用修复后的 `.env`（glm-4v-flash）发 1×1 PNG 请求 → `status=200`。
2. `systemctl is-active error-learn-api` = `active`；启动日志包含视觉模型 base/model。
3. 微信**体验版**真机拍照识别 → 成功返回题干/解答；`journalctl` 中 `POST /api/v1/recognize` 为 200 且无 `vision upstream` warning。
4. 本地真机：`npm run server` 启动后拍照识别成功。
5. 回滚验证方式：保留的 `.env.bak-20261110` 与两个 `.py.bak-20261110` 可一键还原。
