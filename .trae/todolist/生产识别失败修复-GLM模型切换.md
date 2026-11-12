# 本次会话任务进度（todo）

> 主题：还是不行——AI_ENABLED / 欠费 / 模型与地址排查，生产切换 GLM-4V-Flash
> 任务总数：4 ｜ 已完成：4 ｜ 未完成：0
> 会话日期：2026-11-10

## 任务清单

| # | 任务 | 状态 |
| --- | --- | --- |
| 1 | 备份并修改生产 `.env`（GLM-4V-Flash，免费） | ✅ 已完成 |
| 2 | 对比并同步生产后端可诊断代码（`vision_recognize.py`、`main.py`） | ✅ 已完成 |
| 3 | 重启生产服务并验证（远端探针 + 端到端识别） | ✅ 已完成（HTTP 200 / code 0） |
| 4 | 更新部署文档、change-log 与会话 todo | ✅ 已完成 |

## 结论

- `AI_ENABLED=false` **不是**原因：该字段仅解析、从未被业务引用。
- **不是欠费**：生产 Key 调 `qwen3-vl-plus` 与 `glm-4v-flash` 均返回 200。
- 真正根因：生产使用第三方代理 `https://maas.qianwenaiapi.com/compatible-mode/v1` + `VISION_MODEL=qwen-vl-flash`，该代理不存在此模型，上游返回 404 `Model not exist`，被兜底为「识别失败，请重试或手动输入」。
- 处置：生产已切到智谱免费 `glm-4v-flash` @ `https://open.bigmodel.cn/api/paas/v4`，并同步可诊断代码；端到端识别返回 200 / code 0。
- 本地真机 dev 预览失败是因本地后端未启动（8000 未监听），需先 `npm run server`。

## 模型与地址（当前）

| 环境 | 模型 | 地址 |
| --- | --- | --- |
| 本地 | glm-4v-flash | https://open.bigmodel.cn/api/paas/v4 |
| 生产 | glm-4v-flash | https://open.bigmodel.cn/api/paas/v4 |
| 生产（旧，已废弃） | qwen-vl-flash | https://maas.qianwenaiapi.com/compatible-mode/v1 |
