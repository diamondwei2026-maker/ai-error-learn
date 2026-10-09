# 错题本小程序 MVP 开发计划（Taro 前端 + Python 后端）

> 依据文档：`.docs/需求分析文档.md`、`.docs/方案设计文档.md`、`.docs/UI原型设计方案.md`
> UI 基准：`deepseek-design/错题本原型-01/02/03.html`（v3 轻盈化版）
> 生成工具链：`TRAE-generate-mini-app` Skill（`init-template.js` + `preview-server.js`）

***

## 1. Summary（目标与范围）

交付 **MVP 核心闭环** 的完整可运行代码：

* **前端**：Taro 4.1.9 + React 18 + TypeScript + CSS Modules，仅编译 `weapp`（保留多端扩展位，H5 作为预览降级）。

* **后端**：Python + FastAPI，**仅作 OCR 密钥代理**（阿里云文字识别），错题数据 100% 留本地，**不引入业务数据库**。

* **AI**：本期**不实现**，仅预留可测试的接口（LangChain 接入点以接口/stub 形式预留）。

* **UI**：严格按 `deepseek-design` 三份 HTML 原型还原（配色/字号/圆角/毛玻璃/卡通形象逐项对齐），不自行发挥。

* **流程**：后端全量 **TDD**（先写测试再实现，`pytest` 全绿）。

### 已确认的关键决策（来自人工确认）

| 决策点    | 结论                                                 |
| ------ | -------------------------------------------------- |
| 后端定位   | **仅代理 OCR/AI，业务数据仍存本地**（替代方案文档中的微信云函数）             |
| AI 范围  | **本期不做 AI，仅预留接口**                                  |
| OCR 凭据 | 已有阿里云 AccessKey（**仅经环境变量注入，严禁落库/落文件**）             |
| 存储方案   | 纯本地：`Taro.setStorageSync`（题干/答案/索引）+ 本地文件系统（压缩后原图） |
| UI 依据  | `deepseek-design/`（v3 轻盈化）；`glm-design/` 为旧版，弃用    |

***

## 2. Current State Analysis（现状分析）

* 仓库为**空工程**：仅有 `.docs/`（3 份文档）、`.trae/`（含旧配色重构方案）、`deepseek-design/`、`glm-design/`（HTML 原型）。**无任何** **`package.json`** **/** **`src/`** **/ 后端代码**。

* 原型为 12 屏、3 个 HTML 文件（375×812 手机框、`repeat(auto-fit,minmax(375px,1fr))` 响应式），含完整的 `:root` 设计令牌、毛玻璃四方、内联 SVG 吉祥物「小错题本」。

* 模板能力（来自 Skill `system-prompt.md`）：Taro 4.1.9 / React ^18 / TS ^5.1；样式 **CSS Modules（`*.module.scss`）**；预置 `src/styles/theme.scss`、`src/styles/variables.scss`、`src/services/cloud.ts`；原生 tabBar；设计稿基准 750rpx；编译目标 微信/抖音/支付宝/H5。

* 预览：`preview-server.js` 以非阻塞方式产出 `[TraePreviewUrl]`（Web/H5 预览）。

### 现状与文档的两处偏差（本计划的处理）

1. 方案文档写"OCR 走微信云函数"，本计划改为 **Python 后端 HTTP 代理**（用户已确认）。前端不再使用 `Taro.cloud.callFunction`，改 `Taro.uploadFile` 直传后端。
2. 方案文档用 SCSS 全局类名；Skill 模板强制 **CSS Modules**。本计划**采用 CSS Modules**（模板约束优先），但保留文档的业务分层（`services/repo`、`store`、`types`、`constants`、`utils`）。

***

## 3. 目标工程结构

```
ai-error-learn/                    # Taro 工程根（Skill 模板初始化于此，保留 .docs/等既有目录）
├── config/  project.config.json  package.json  tsconfig.json   # 模板生成，原则上不改
├── .pai/                          # Skill 缓存（自动生成）
├── src/
│   ├── app.ts / app.config.ts / app.scss
│   ├── assets/tabbar/{home,library,quiz}[-selected].svg
│   ├── styles/theme.scss  styles/variables.scss
│   ├── types/question.ts
│   ├── constants/index.ts         # 存储 Key、分页、OCR 后端地址、错误码
│   ├── utils/{id.ts,format.ts,platform.ts,textClean.ts}
│   ├── services/
│   │   ├── repo/{storageRepo.ts,fileRepo.ts}
│   │   ├── questionService.ts
│   │   └── ocrService.ts
│   ├── store/questionStore.ts     # Zustand
│   ├── components/{Mascot,QuestionCard,FlipCard,Empty,ConfirmDialog,ActionSheet,PrimaryButton}/
│   └── pages/{index,library,quiz,edit}/{index.tsx,index.module.scss,index.config.ts}
└── backend/                       # Python 后端（FastAPI）
    ├── app/{main.py,config.py}
    │   ├── api/{ocr.py,ai.py}
    │   ├── services/{aliyun_ocr.py,ai_service.py}
    │   ├── models/schemas.py
    │   └── utils/text_clean.py
    ├── tests/{conftest.py,test_text_clean.py,test_aliyun_ocr.py,test_ocr_api.py,test_ai_api.py,test_config.py}
    ├── requirements.txt  requirements-ai.txt  .env.example  pytest.ini
```

***

## 4. Proposed Changes（分步实施）

> 执行顺序：Step 0 → 8。Step 0/1 为前置，Step 2 后端（TDD），Step 3–7 前端，Step 8 预览。
> **约束**：前端生成严格遵循 Skill `system-prompt.md` 七阶段与质量门禁；**不调用子智能体、不使用 TodoWrite**（Skill 硬性要求）；**禁止执行任何 Taro/NPM 原生命令**，初始化与预览只能走 Skill 脚本。

### Step 0 · 技能资产绑定与模板初始化（前端地基）

1. 执行 `node d:\Users\weij\.trae-cn\builtin_skills\TRAE-generate-mini-app/scripts/get-skill-assets-dir.js`，取得 `skill_assets_dir`（写入 `.pai/`）。
2. 执行 `node ${skill_assets_dir}/scripts/init-template.js`（默认当前目录）初始化 Taro 模板。
3. 读取并确认模板实际落盘结构：`package.json`、`src/styles/theme.scss`、`src/styles/variables.scss`、`src/services/cloud.ts`、`src/pages/index/*`。
4. 产出：可运行的空壳 Taro 工程。

### Step 1 · 拉取官方最新用法（确保 API 正确）

在写代码前，用 WebFetch/WebSearch 核对以下最新用法（优先官方文档）：

* Taro 4.x：`Taro.chooseMedia` / `compressImage` / `getFileSystemManager` / `uploadFile` / `request` / `setStorageSync` / `useRouter` / `defineAppConfig`（docs.taro.zone）。

* 阿里云 OCR Python SDK：`alibabacloud_ocr_api20210707` + `RecognizeGeneral`/`RecognizeAdvanced` 调用形态（help.aliyun.com / API 参考）。

* FastAPI：`UploadFile`/`File` 接收 multipart、`CORSMiddleware`、`TestClient`。

* LangChain：仅确认预留接口形态，不引入依赖。

> 若 Context7 不可用（当前未配置该 MCP），一律以官网文档为准，并在代码注释中标注依据的 API 形态。

### Step 2 · Python 后端（TDD，先测后码）

**技术选型**：FastAPI + Uvicorn + Pydantic v2 + alibabacloud\_ocr\_api20210707；测试 pytest + httpx（`TestClient`）。

**接口设计**（对齐方案文档 §7.1）

| 方法   | 路径                    | 说明                                                    |
| ---- | --------------------- | ----------------------------------------------------- |
| GET  | `/api/v1/health`      | 健康检查 `{status:"ok"}`                                  |
| POST | `/api/v1/ocr`         | multipart 字段 `file`（图片）→ `{code,text,wordsCount}`     |
| POST | `/api/v1/ai/variants` | **预留**：返回 `{code:9001, message:"AI 功能未启用"}`, HTTP 501 |

**OCR 错误码**：`0` 成功 / `1001` 图片下载失败 / `1002` OCR 调用失败 / `1003` 配额超限 / `1004` 图片过大（>10MB）。

**模块职责**

* `utils/text_clean.py`：纯函数——去多余空白、合并换行、去行首尾噪声、统计字数。

* `services/aliyun_ocr.py`：封装 SDK；**依赖注入 client**（便于 mock）；先 `RecognizeAdvanced` 失败回退 `RecognizeGeneral`；把 SDK 异常映射为 1001/1002/1003。

* `services/ai_service.py`：定义 `VariantGenerator` Protocol + `DisabledVariantGenerator`（抛出未启用）；注释标注 LangChain 接入点。

* `config.py`：从环境变量读 `ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET`、`OCR_ENDPOINT`、`MAX_IMAGE_BYTES`；**不打印、不落盘密钥**。

* `main.py`：装配路由、CORS（开发放开）、异常兜底。

**TDD 测试用例（先写，须全绿）**

* `test_text_clean.py`：空串、全空白、多换行合并、行首尾空格、字数统计。

* `test_aliyun_ocr.py`：mock client 成功返回→拼接文本；Advanced 失败→回退 General；SDK 抛错→1002；限流/配额→1003；空结果→`text=""`。

* `test_ocr_api.py`：上传合法图片→`code=0` 且文本非空；非图片/空文件→1004；超大文件→1004；服务层异常→1002。

* `test_ai_api.py`：`/ai/variants` 返回 501 + `code=9001`。

* `test_config.py`：缺失密钥时启动不崩溃（仅 OCR 调用时报错），密钥不进日志。

**运行验证**：`cd backend; python -m pytest -q` 全绿。

### Step 3 · 前端全局配置（Skill 第五阶段）

* `src/styles/theme.scss`：写入 UI 规范 §3.2 全部令牌（`#07C160/#06AD56/#056B36/#F0FBF5/#E4F8EE/#2563A8/#12A8F0/#EFF8FE/#0A6BA8/#F5943C/#96530E/#F5514E/#BE322F/#1F2937/#4B5563/#6B7280/rgba(17,24,39,.07)` 等）。

* `src/styles/variables.scss`：间距 S/M/L/XL、圆角小/中/大/胶囊、`--elev` 与 float 阴影、字体栈（**中文系统字体栈，禁用等宽**）、`tabular-nums` mixin。

* `src/app.config.ts`：4 个页面（`pages/index/index`、`pages/library/index`、`pages/quiz/index`、`pages/edit/index`）+ **3 tab 原生 tabBar**（首页/题库/刷题），window 白底黑字。

* `src/assets/tabbar/`：生成 `home/library/quiz` 的默认态与选中态 SVG（选中态用主题绿，线条风格统一，viewBox 0 0 24 24）。

* `src/app.scss`：页面基础样式（`page` 底色 `#FAFBFD`、字体栈）。

* 产出：全局配置齐全，为后续页面提供统一令牌。

### Step 4 · 前端类型 / 常量 / 工具 / 服务层

* `types/question.ts`：`Question`、`AppMeta`（字段同方案文档 §4.1）。

* `constants/index.ts`：`STORAGE_KEYS`（`q:list`/`q:meta`/`q:schema`）、`PAGE_SIZE`、`OCR_API_BASE`（默认 `http://127.0.0.1:8000`，可被 `process.env.TARO_APP_OCR_API_BASE` 覆盖）、OCR 错误码文案映射。

* `utils/id.ts`（时间戳+随机串）、`utils/format.ts`（时间/字数）、`utils/platform.ts`（weapp 判定 `process.env.TARO_ENV`）。

* `services/repo/storageRepo.ts`：同步读、异步/节流写；`listQuestions/saveQuestions/getMeta/saveMeta`。**页面禁止直接调** **`Taro.setStorage`**。

* `services/repo/fileRepo.ts`：

  * weapp：`getFileSystemManager` 落盘 `${USER_DATA_PATH}/q_{id}.jpg`，`saveImage/removeImage/calcUsage/clearOrphans`。

  * H5（预览降级）：以 base64 dataURL 存 Storage，接口签名一致。

* `services/questionService.ts`：`create/list/get/remove/pickRandom(excludeIds)/count`；`pickRandom` 用 **Fisher-Yates + 本轮已抽集合**（不改页面接口，仅内部实现）。

* `services/ocrService.ts`：weapp `Taro.uploadFile` → 后端 `/api/v1/ocr` → 返回文本；失败/超时**不阻断**，返回 `{ok:false}` 由编辑页兜底提示"识别失败，请手动输入"；H5 预览走同接口，后端不可达时降级。

* `store/questionStore.ts`：Zustand 维护题目列表、总数、加载态，跨页共享。

### Step 5 · 前端通用组件（严格对齐原型）

每个组件 `index.tsx` + `index.module.scss`（camelCase 类名 + classnames）：

* `Mascot/`：内联 SVG「小错题本」（圆角笔记本 + 绿描边 `#0E8F52` + 橙色书签 `#FFC078` + 腮红 `#FFC7A6`），`floaty` 4.5s 浮动，遵循 `prefers-reduced-motion`。

* `QuestionCard/`：白底 + 1px 淡描边 + 12px 圆角 + `--elev` 阴影；题干 2 行截断 + 含原图角标 + 时间。

* `FlipCard/`：纯 CSS 3D 翻面（`perspective:1000px` + `rotateY(180deg)` + `backface-visibility:hidden`，0.4s），正面遮挡答案（虚线 + 斜纹 + 锁图标），背面答案 + 原图。

* `Empty/`：吉祥物 + 主/副文案 + 行动按钮。

* `ConfirmDialog/`：居中卡片 280px + 16px 圆角 + 遮罩 `rgba(15,23,42,.30)` + `blur(2px)`。

* `ActionSheet/`：底部弹层 + 毛玻璃 `rgba(255,255,255,.92)` + `blur(30px)`。

* `PrimaryButton/`：胶囊主按钮（高 50px，17/600），`&:active` 反馈。

### Step 6 · 前端页面（Skill 第六阶段，逐页 6 步流程）

四页各 3 文件，UI 逐屏对齐 `deepseek-design`：

| 页面  | 目录              | 对齐原型                | 要点                                                            |
| --- | --------------- | ------------------- | ------------------------------------------------------------- |
| 首页  | `pages/index`   | 文件1 · 01 屏          | 品牌区 + 吉祥物 + 数据概览（错题总数，**不展示容量**）+ 两个主入口卡片 + tabBar            |
| 编辑页 | `pages/edit`    | 文件1 · 04/05 屏       | 原图缩略（可预览）+ 题干框(≥160px) + 答案框(≥100px) + 吸底毛玻璃"保存入库"；题干空不可存     |
| 题库  | `pages/library` | 文件2 · 06/07/08/09 屏 | 顶部题量 + 卡片分页（`onReachBottom`）+ 左滑删除 + FAB + 空态 + 详情预览 + 删除二次确认 |
| 刷题  | `pages/quiz`    | 文件3 · 10/11/12 屏    | 进度(第 x/y)+进度条 + 卡片正面遮挡 + 点击/按钮 3D 翻面 + 本轮完成页                  |

* 录入链路（首页 → ActionSheet 拍照/相册 → OCR → 编辑页）按方案文档 §6.1/§6.2 实现；OCR 失败不阻断。

* 保存成功用 **浅色胶囊 Toast**（原型 05 屏）后返回题库。

* 所有 weapp 专属 API 用 `process.env.TARO_ENV === 'weapp'` 包裹，非微信端走降级，保证 H5 预览不白屏。

### Step 7 · 代码检查（Skill 第七阶段质量门禁）

逐项自查：文件完整性、导入完整性、依赖完整性、SCSS 变量规范（每个 `.module.scss` 以 `@use '@/styles/variables.scss' as *;` 开头）、配置一致性（`app.config.ts` 与页面/tabBar 图标一一对应）、语法正确性、占位页规范。发现问题立即修复，直至全部通过。用 `GetDiagnostics` 复核无错误。

### Step 8 · 预览与交付

* 非阻塞启动 `node ${skill_assets_dir}/scripts/preview-server.js`，解析 `[TraePreviewUrl]`。

* 调 `OpenPreview` 打开预览，输出统一「开发完成总结」。

***

## 5. Assumptions & Decisions（假设与决策）

1. **UI 基准目录**：以 `deepseek-design/` 为准（其与 UI 文档 v1.3、配色重构方案一致）；`glm-design/` 弃用。若不符请指正。
2. **后端框架**：选 FastAPI（生态成熟、`TestClient` 便于 TDD）。若你偏好 Flask，请在评审时提出。
3. **前端通信**：`Taro.uploadFile` 单次 multipart 直传后端（替代"先传云存储再传 fileID"两步），更轻；错题原图仍先落本地文件系统。
4. **H5 预览降级**：weapp 专属 API（FS/compressImage/chooseMedia）在 H5 走降级实现（Taro.chooseImage + base64 存储 + 同后端接口），仅用于预览评审，不影响 weapp 主链路。
5. **密钥安全**：AccessKey 仅通过环境变量注入后端，仓库只提供 `.env.example` 占位；**不得写入任何源码/配置文件**。⚠️ 已提示你轮换本次对话中暴露的密钥。
6. **AI 预留**：仅接口 + stub + `requirements-ai.txt`（含 langchain，默认不安装），不实现真实 LLM 调用。
7. **不引入**：NutUI（UI 极简，自研组件）、富文本/公式、账号体系、云数据库。
8. **模板改动边界**：`config/`、`tsconfig.json`、`babel.config.js`、`project.config.json` 不改；`package.json` 仅在需新增依赖时追加（如 zustand、classnames）。

***

## 6. Verification（验收步骤）

**后端**

1. `cd backend; python -m pytest -q` → 全部通过。
2. `uvicorn app.main:app --port 8000` 启动；`GET /api/v1/health` 返回 `{"status":"ok"}`。
3. 有 Key 时用一张试卷图 `POST /api/v1/ocr` → `code=0` 且返回清洗后文本（真实联网冒烟，非必跑）。
4. `/api/v1/ai/variants` → HTTP 501 + `code=9001`。

**前端**
5\. Skill 预览服务启动并 `OpenPreview` 成功，无白屏。
6\. 逐屏比对 `deepseek-design`：配色/字号/圆角/毛玻璃四处/吉祥物 5 处出现位置一致。
7\. 闭环自测（weapp 或 H5）：新增 5 题 → 题库可见并分页 → 刷题随机抽题可翻面 → 左滑删除生效并同步清理图片 → 空态与完成页正确。
8\. `GetDiagnostics` 全绿；`app.config.ts` 页面/tabBar 图标文件一一对应。

**质量门禁**：Step 7 七项检查全部通过后方可启动预览。

***

## 7. 交付物清单

* 可运行的 Taro（weapp）前端工程（4 页面 + 7 通用组件 + 服务/存储分层）。

* Python FastAPI 后端（OCR 代理 + AI 预留接口）+ 全量 TDD 测试。

* `.env.example`（占位，无真实密钥）。

* 预览链接与开发完成总结。

