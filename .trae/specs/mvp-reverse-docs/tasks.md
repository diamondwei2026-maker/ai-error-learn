# 错题本小程序 MVP · 任务盘点（Tasks）

> **本文档仅为"功能盘点"，不是排期计划、不包含任何编码任务、不触发任何开发动作。**
> 用途：区分「已完成 MVP 功能」与「下一阶段迭代待办」，供人工评审对照。
> 依据：仓库现有可运行代码（`client/` + `server/`）。凡代码中不存在的功能，一律不计入"已完成"。

---

## 一、【已完成 MVP 功能清单】

> 全部条目均可在代码中定位到实现；勾选表示**代码已实现**（非"已上线验收"）。

### 1. 工程与基础设施

- [x] 1.1 前端工程初始化：Taro 4.1.9 + React 18 + TypeScript + SCSS + CSS Modules（`client/package.json`、`client/config/index.ts`）
- [x] 1.2 多端判定与编译期分支：`isWeapp` / `isH5`（`client/src/utils/platform.ts`）
- [x] 1.3 设计令牌体系：主题色、间距、圆角、阴影、毛玻璃、字体栈（`client/src/styles/theme.scss`、`variables.scss`、`compat.scss`）
- [x] 1.4 后端工程：FastAPI 应用装配 + CORS + 健康检查（`server/app/main.py`）
- [x] 1.5 后端配置装载：环境变量/`.env`（override），密钥 `repr=False` 防泄露（`server/app/config.py`）
- [x] 1.6 后端 TDD 单测：text_clean / vision_recognize / recognize_api / ai_api / config（`server/tests/**`）

### 2. 页面（4 个）

- [x] 2.1 首页：品牌区 + 吉祥物 + 错题总数统计 + 两个主入口（`pages/index/index.tsx`）
- [x] 2.2 编辑校对页：识别进度态 + 表单校对 + 保存入库（`pages/edit/index.tsx`）
- [x] 2.3 题库页：卡片列表 + 分页 + 详情预览 + 删除 + FAB + 空态（`pages/library/index.tsx`）
- [x] 2.4 刷题页：随机抽题 + 遮挡 + 3D 翻面 + 本轮完成页（`pages/quiz/index.tsx`）
- [x] 2.5 原生 tabBar（首页/题库/刷题）与自定义导航栏样式（`app.config.ts`、`components/NavBar`）

### 3. 通用组件（11 个）

- [x] 3.1 基础 UI：`NavBar`、`AppButton`、`Chip`、`Icon`、`Mascot`
- [x] 3.2 业务 UI：`QuestionCard`、`FlipCard`、`SwipeItem`
- [x] 3.3 交互反馈：`ActionSheet`、`ConfirmDialog`、`Empty`

### 4. 题目采集与识别

- [x] 4.1 拍照 / 相册选图（weapp：`chooseMedia`；非 weapp：`chooseImage`）（`services/captureService.ts`）
- [x] 4.2 图片压缩（weapp：`compressImage`，quality=70，width=1080）
- [x] 4.3 图片上传后端识别（`Taro.uploadFile` → `POST /api/v1/recognize`，30s 超时）（`services/recognitionService.ts`）
- [x] 4.4 后端多模态一步识别「题干 + 解答（含解题过程）」（`server/app/services/vision_recognize.py`）
- [x] 4.5 后端模型输出解析容错（去围栏 / 截取 JSON / `strict=False`，失败整段落题干）（`_parse_content`）
- [x] 4.6 后端文本清洗与字数统计（`server/app/utils/text_clean.py`）
- [x] 4.7 识别错误码映射：1002/1003/1004/1005（`vision_recognize` + `api/recognize.py`）
- [x] 4.8 识别失败/超时不阻断主流程，编辑页兜底手动输入（`pages/edit/index.tsx`）
- [x] 4.9 重拍能力（编辑页右上「重拍」重新采集并识别）

### 5. 本地入库与数据管理

- [x] 5.1 错题数据模型 `Question` / `AppMeta`（`types/question.ts`）
- [x] 5.2 Storage 读写封装（`q:list` / `q:meta` / `q:schema`）（`services/repo/storageRepo.ts`）
- [x] 5.3 图片本地持久化（weapp 文件系统 `${USER_DATA_PATH}/q_{id}.jpg`；H5 base64）（`services/repo/fileRepo.ts`）
- [x] 5.4 新建错题：先落图片 → 写列表 → 更新 meta（`questionService.create`）
- [x] 5.5 分页查询 / 全量查询 / 按 id 查询（`questionService.list/all/get`）
- [x] 5.6 删除错题：删列表项 + 同步删原图 + 回写 meta（`questionService.remove`）
- [x] 5.7 题干非空校验（不足则不可保存）（`pages/edit`）
- [x] 5.8 保存成功 Toast 并自动跳转题库（`pages/edit`）
- [x] 5.9 启动清理无主图片（`app.tsx` + `fileRepo.clearOrphans`）
- [x] 5.10 跨页错题总数共享（Zustand：`store/questionStore.ts`）

### 6. 题库管理交互

- [x] 6.1 卡片列表（题干 2 行截断 + 含原图角标 + 时间）
- [x] 6.2 触底分页加载（每页 10）
- [x] 6.3 详情预览（题干 / 原图大图预览 / 答案），详情态隐藏 tabBar
- [x] 6.4 左滑删除 + 长按删除，均走二次确认弹窗
- [x] 6.5 空态引导（去录入第一道错题）
- [x] 6.6 FAB 新增录入入口

### 7. 刷题复习交互

- [x] 7.1 随机抽题：Fisher-Yates 洗牌 + 本轮已抽集合（一轮内不重复，抽完自动重置）（`questionService.pickRandom`）
- [x] 7.2 正面遮挡答案（锁图标 + 提示）
- [x] 7.3 纯 CSS 3D 翻面（点击卡片/按钮，0.4s），背面显示答案 + 原图
- [x] 7.4 进度显示（第 x/y 题 + 进度条）与本轮计时器
- [x] 7.5 下一题逻辑与"本轮完成页"（题数 + 用时 + 再来一轮/返回题库）
- [x] 7.6 题库为空时的空态引导

### 8. 后端接口

- [x] 8.1 `GET /api/v1/health` 健康检查
- [x] 8.2 `POST /api/v1/recognize` 识别接口（multipart）
- [x] 8.3 请求体校验：空文件 / 超限 / 非图片 → 1004
- [x] 8.4 `POST /api/v1/ai/variants` 预留接口（固定 HTTP 501 / code 9001）
- [x] 8.5 服务层依赖注入（client 可注入便于 mock 单测）

### 9. 部署与联调

- [x] 9.1 后端启动脚本（`client/package.json` 的 `npm run server`，含依赖检查，Windows 专用）
- [x] 9.2 `.env.example` 配置模板（无真实密钥）
- [x] 9.3 H5 预览降级链路（图片 base64 + 同后端接口）

---

## 二、【下一阶段迭代待办清单】

> 以下条目**当前代码中不存在或未接通**。本清单仅作盘点，**不排期、不实现、不触发开发**。
> 来源标注：`[设计文档]`=原始需求/方案中已规划；`[代码缺口]`=逆向发现的实现缺陷（详见 spec.md §8）。

### A. 稳定性与工程债（建议优先）

- [ ] A.1 后端地址可配置化（去除硬编码局域网 IP；支持环境变量注入）`[代码缺口 §8.2-1]`
- [ ] A.2 后端识别接口鉴权与 CORS 收敛（防密钥代理被滥用）`[代码缺口 §8.2-2]`
- [ ] A.3 本地容量阈值告警与保存前容量校验 `[代码缺口 §8.2-3]`
- [ ] A.4 清理死代码/未接通预留（`cloud.ts`、`calcUsage`、`formatBytes`、`supportsFileSystem`、`AiResponse`）`[代码缺口 §8.2-4/5]`
- [ ] A.5 补齐前端自动化测试 `[代码缺口 §8.2-9]`

### B. 数据能力增强

- [ ] B.1 错题编辑功能（当前仅有新建/删除；`updatedAt` 未启用）`[代码缺口 §8.2-6]`
- [ ] B.2 数据结构迁移机制（`schemaVersion` 仅写入，无迁移）`[代码缺口 §8.2-7]`
- [ ] B.3 大列表分片/性能优化（当前为全量读 + 切片）`[代码缺口 §8.2-8]`
- [ ] B.4 图片上云存储降级方案（`fileRepo` 层替换）`[设计文档]`

### C. 体验完善

- [ ] C.1 编辑页手动"拆分题干/答案"兜底能力 `[设计文档]`
- [ ] C.2 识别失败时的更好兜底（如重试引导）`[代码缺口 §8.2-13]`
- [ ] C.3 《用户隐私保护指引》配置与首启授权引导 `[设计文档]`
- [ ] C.4 H5 预览链路优化（图片压缩/配额）`[代码缺口 §8.2-12]`

### D. 新功能（按原始需求优先级，均为从 0 到 1）

- [ ] D.1 **[高]** 账号与订阅管理（微信登录 / 云同步 / 会员），需企业主体与微信支付 `[设计文档]`
- [ ] D.2 **[高]** 题目多维分类（学科 / 自定义标签）与筛选 `[设计文档]`
- [ ] D.3 **[中]** 学习数据与掌握度标记（正确率统计、复习热力图）`[设计文档]`
- [ ] D.4 **[中]** 科学复习引擎（艾宾浩斯遗忘曲线 + 待复习推送）`[设计文档]`
- [ ] D.5 **[低]** AI 变式题生成（接入 LLM，替换预留 stub）`[设计文档 + 代码预留]`
- [ ] D.6 **[低]** 知识库题目生成（文档上传 → 结构化出题）`[设计文档]`

---

## 三、清单统计

| 分类 | 数量 |
| --- | --- |
| 已完成 MVP 功能（条目） | 9 类 / 共 48 条 |
| 下一阶段待办（条目） | 4 类 / 共 17 条 |

> 说明：以上"已完成"以**代码实现存在**为准，不代表已通过真机/审核验收；验收口径见同目录 `checklist.md`。
