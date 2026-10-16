# incr-20261016-内容安全接入 · 任务拆解

> 依据：`.trae/documents/微信内容安全接入改造方案.md` §10 执行顺序
> 状态：全部完成（2026-10-16）

| #   | 任务                             | 关联文件                                                          | 状态 |
| --- | -------------------------------- | ----------------------------------------------------------------- | ---- |
| 1   | 配置与错误码                     | `app/config.py`、`app/errors.py`                                  | 完成 |
| 2   | access_token 缓存 + 内容安全服务 | `app/services/content_security.py`                                | 完成 |
| 3   | 图片校验记录表                   | `app/models/media_check.py`、`app/db/session.py`                  | 完成 |
| 4   | 请求模型                         | `app/models/schemas.py`                                           | 完成 |
| 5   | 文本预检接口                     | `app/api/security.py`                                             | 完成 |
| 6   | 消息推送回调                     | `app/api/wechat_callback.py`                                      | 完成 |
| 7   | 昵称校验                         | `app/api/user.py`                                                 | 完成 |
| 8   | 头像异步送检                     | `app/api/user.py`                                                 | 完成 |
| 9   | 错题文本兜底校验                 | `app/api/sync.py`                                                 | 完成 |
| 10  | 应用装配                         | `app/main.py`                                                     | 完成 |
| 11  | 测试夹具                         | `tests/conftest.py`                                               | 完成 |
| 12  | 内容安全单测                     | `tests/test_content_security_api.py`                              | 完成 |
| 13  | 配置单测补充                     | `tests/test_config.py`                                            | 完成 |
| 14  | 前端错误码与文案                 | `client/src/constants/index.ts`、`client/src/services/request.ts` | 完成 |
| 15  | 前端预检服务                     | `client/src/services/securityService.ts`                          | 完成 |
| 16  | 保存前预检接入                   | `client/src/pages/edit/index.tsx`                                 | 完成 |
| 17  | 同步 rejected 日志               | `client/src/services/syncService.ts`                              | 完成 |
| 18  | 环境变量模板                     | `server/.env.example`、`deploy/env.production.example`            | 完成 |
| 19  | 回归验证                         | pytest（105 passed）+ tsc + build:weapp                           | 完成 |
| 20  | 变更索引                         | `.trae/docs/change-log.md`                                        | 完成 |

## 执行中相对方案的两处微调（均为去噪，不改变行为）

1. `create_wechat_callback_router(settings)` —— 回调无需 `content_security`，故去掉该未使用参数（方案原文为 `(settings, content_security)`）。
2. `api/user.py` 注销账号时**额外清理** `media_check_record`（与既有 `QuestionSync` 级联删除同模式）——避免 user_id 复用后，迟到的图片回调误删新用户头像（方案 §4.7 已含"防误删"意图，此处补齐数据侧清理）。
