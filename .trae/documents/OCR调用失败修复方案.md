# OCR 调用失败修复方案

## 1. Summary（目标与范围）

定位并修复「小程序调用 OCR 失败」的问题。经实测复现，**根因不在代码，而在阿里云账号侧**：当前使用的 AccessKey 所属主账号**未开通「文字识别 OCR」（ocr-api）服务**，阿里云直接返回 `ocrServiceNotOpen`（401）。

本方案分两部分：

- **A. 账号侧（实际修复，需用户操作）**：在正确的主账号上开通 OCR 服务并给 RAM 用户授权。
- **B. 代码侧（可诊断性改进，我实现）**：把「服务未开通/无权限」这类错误从笼统的 `1002 识别失败` 提升为明确的错误码与文案，避免下次再出现「看不出为什么失败」的情况。

## 2. Current State Analysis（现状与根因）

### 2.1 实测复现

用 `server/.env` 中的密钥直接调用 `AliyunOcrClient.recognize()`（advanced / general 两种模式），均失败：

```
advanced EXC code=ocrServiceNotOpen | msg=code: 401, You have not activated the OCR service.
general  EXC code=ocrServiceNotOpen | msg=code: 401, You have not activated the OCR service.
```

### 2.2 账号身份实测（STS GetCallerIdentity）

```
IdentityType: RAMUser
AccountId:    1482113135155712          # 主账号 UID
Arn:          acs:ram::1482113135155712:user/power-application-wj
```

### 2.3 结论

- AccessKey **本身有效**（若密钥无效，阿里云会返回 `InvalidAccessKeyId` / `SignatureDoesNotMatch`，而不是 `ocrServiceNotOpen`）。
- `ocrServiceNotOpen` 是**账号级**错误：主账号 `1482113135155712` 尚未开通 OCR 服务；或服务开通在**另一个阿里云账号**上。
- 代码链路本身正确：[aliyun_ocr.py](file:///d:/Users/weij/ai-error-learn/server/app/services/aliyun_ocr.py#L102-L133) 中 SDK 方法名（`recognize_advanced_with_options` / `recognize_general_with_options`）、请求构造（`RecognizeAdvancedRequest(body=stream)`）、endpoint（`ocr-api.cn-hangzhou.aliyuncs.com`）经核对与已安装 SDK `alibabacloud-ocr-api20210707 3.1.3` 一致；密钥加载与校验也正常。
- 可诊断性缺陷：[aliyun_ocr.py](file:///d:/Users/weij/ai-error-learn/server/app/services/aliyun_ocr.py#L68-L75) 的 `_map_to_ocr_error` 把该类错误归入 `1002 识别失败，请重试或手动输入`，且 [OcrService](file:///d:/Users/weij/ai-error-learn/server/app/services/aliyun_ocr.py#L142-L161) 仍会做一次无意义的通用版降级重试，导致前端只看到「识别失败」，无法判断是账号未开通。

## 3. Proposed Changes（具体改动）

### 3.1 账号侧：开通 OCR 并授权（用户执行，实际修复）

在**主账号 `1482113135155712`** 上操作（务必确认控制台右上角「账号 ID」= 1482113135155712，而非个人其它账号）：

1. **开通文字识别 OCR 服务**：登录阿里云控制台 → 访问 https://ocr.console.aliyun.com/ → 点击「开通/立即开通」，产品为「文字识别 OCR」（对应 `ocr-api`）。
   - 注意：若此前只在云市场开通过「读光OCR/旧版 OCR」，**不算**开通本服务，需按上面入口重新开通。
2. **给 RAM 用户授权（不用 `AliyunOCRFullAccess`，改用最小权限自定义策略）**：
   - `AliyunOCRFullAccess` 是「全量访问」系统策略，阿里云会弹「高风险」提示拦截，**不要**用它。
   - 改为自定义策略：RAM 控制台 → 「权限策略」→ 创建策略 → 「脚本编辑」，粘贴下面 JSON（RamCode = `ocr`，仅放开本项目实际调用的两个 API）：

     ```json
     {
       "Version": "1",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "ocr:RecognizeAdvanced",
             "ocr:RecognizeGeneral"
           ],
           "Resource": ["*"]
         }
       ]
     }
     ```

   - 策略名建议 `OcrProxyReadOnly` → 保存 → 回到用户 `power-application-wj` → 「权限管理」→ 新增授权 → 选择该**自定义策略**。
   - 说明：OCR 为「操作级」授权、不支持资源级授权，`Resource` 必须为 `["*"]`；只列 2 个 Action 属最小权限，不会再触发 `AliyunOCRFullAccess` 的高风险拦截。
3. **确认站点与地域**：账号须为中国站（aliyun.com）；`.env` 端点保持 `ocr-api.cn-hangzhou.aliyuncs.com`（华东1·杭州）。
4. **等待生效**后按 §5 重跑诊断命令验证。

> 该部分无法由代码完成；若开通后仍报 `ocrServiceNotOpen`，通常是「开通的账号不是 1482113135155712」。

### 3.2 代码侧：错误可诊断（我执行）

**改动文件 1：`server/app/services/aliyun_ocr.py`**

- 新增业务错误码常量（对齐 `.docs/方案设计文档.md` §7.1）：
  ```python
  CODE_SERVICE_UNAVAILABLE = 1005  # 服务未开通 / 无权限 / 鉴权失败
  ```
- 新增鉴权/未开通判定关键字（去空格小写后匹配，兼容 `ocrServiceNotOpen`、`NoPermission`、`Forbidden`、`InvalidAccessKeyId`、`SignatureDoesNotMatch`、`Unauthorized` 等）。
- 修改 `_map_to_ocr_error` 判定顺序：配额（1003）→ **服务未开通/无权限（1005，文案「OCR 服务未开通或无权限，请检查阿里云账号配置」）** → 其它（1002）。
- 修改 `OcrService.recognize`：当映射结果为 `CODE_SERVICE_UNAVAILABLE` 时**立即上抛、不再做通用版降级**（与现有 1003 的处理方式一致），避免一次无谓请求。

**改动文件 2：`client/src/constants/index.ts`**

- 在 `OCR_ERROR_MESSAGES` 中新增 `1005: 'OCR 服务未开通或无权限，请联系管理员'`。
  （后端已通过 `message` 字段返回具体文案，[ocrService.ts](file:///d:/Users/weij/ai-error-learn/client/src/services/ocrService.ts#L38-L43) 会优先展示它；此项仅作兜底。）

**改动文件 3：`server/tests/test_aliyun_ocr.py`**

- 新增用例：`FakeSdkError("ocrServiceNotOpen", "...")` → 期望抛出 `OcrError` 且 `code == CODE_SERVICE_UNAVAILABLE`，且 `client.calls == ["advanced"]`（验证不降级）。

**改动文件 4：`.docs/方案设计文档.md` §7.1 错误码表**

- 新增一行：`| 1005 | 服务未开通 / 无权限 | 提示联系管理员 |`，保持文档与实现一致。

## 4. Assumptions & Decisions（假设与决策）

1. **不更换 OCR 服务商**：用户已确认可自行在阿里云开通，故仍使用阿里云。
2. **RAM 授权采用最小权限自定义策略**：因 `AliyunOCRFullAccess` 触发「高风险」拦截，改为只授予 `ocr:RecognizeAdvanced`、`ocr:RecognizeGeneral` 的自定义策略。若后续新增其它 OCR 能力（如 `RecognizeAllText`），需在策略 Action 中追加对应权限点。
3. **错误码 1005 复用现有机制**：前端 `OCR_ERROR_MESSAGES` 为字典，新增键成本极低；且后端 `message` 已优先展示，改动最小。
4. **1005 不降级**：鉴权/未开通属账号级错误，通用版必然同样失败，故短路跳过降级。
5. **不新增接口/文件**：仅在既有文件内修改，遵循「改文档化、少加文件」。
6. **真机注意**（非本次根因，仅提示）：[constants/index.ts](file:///d:/Users/weij/ai-error-learn/client/src/constants/index.ts#L14-L18) 的 `OCR_API_BASE` 为 `http://127.0.0.1:8000`，仅适用于微信开发者工具（需勾选「不校验合法域名」）；真机需改为局域网 IP/HTTPS 域名并在小程序后台配置 request/uploadFile 合法域名。本次不改。

## 5. Verification（验收步骤）

1. **账号开通前（复现基线）**：执行诊断命令，应仍返回 `ocrServiceNotOpen`。
2. **账号开通后**：重跑同一诊断命令，期望**不再是 `ocrServiceNotOpen`**（因传入的是伪造字节，应转为图片解析类错误，如 `InvalidImage` / 参数错误），即证明服务已开通。
3. **单元测试**：在 `server/` 下执行 `..\.venv\Scripts\python.exe -m pytest`（或 `server/.venv\Scripts\python.exe -m pytest`），全部通过，含新增的 1005 用例。
4. **端到端**：`npm run server` 启动后端 → 访问 `http://127.0.0.1:8000/api/v1/health` 返回 `{"status":"ok"}` → 开发者工具中拍照上传，OCR 返回 `code:0` 与识别文本。
5. `GetDiagnostics` 确认改动的 TS / Python 文件无语法错误。

---

**诊断命令（可复用于验收）**：读取 `server/.env` 密钥后调用 `AliyunOcrClient.recognize(b'not-a-real-image', mode)`，打印返回的 `code` 与 `message`。
