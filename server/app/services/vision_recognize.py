"""多模态识别服务：调用轻量级视觉大模型一步识别题干与完整解答（含解题过程）。

分层：
- VisionClient：OpenAI 兼容（/chat/completions）视觉端点适配器（httpx，无新增依赖）
- VisionRecognizeService：业务编排，把调用异常映射为业务错误码

测试阶段使用 GLM-4V-Flash，上线切换为 Qwen-VL-Flash，均通过配置切换，无需改代码。
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from app.utils.text_clean import clean_text

# 业务错误码（沿用原数值，前端文案无需改码）
CODE_RECOGNIZE_FAILED = 1002
CODE_QUOTA_EXCEEDED = 1003
CODE_IMAGE_TOO_LARGE = 1004
CODE_SERVICE_UNAVAILABLE = 1005  # 服务未开通 / 无权限 / 鉴权失败

_DEFAULT_MIME = "image/jpeg"

# 识别 + 拆题提示词：约束模型只输出题干与完整解答的 JSON（解答需保留解题过程）
_PROMPT = (
    "你是题目识别助手。请识别图片中的题目内容，并拆分为「题干」与「解答」两部分。"
    "其中「解答」需完整保留图片中给出的解题过程（含每一步推导、计算与最终结论），"
    "按原有顺序与换行输出，不要只提取最终答案；若图片只有最终答案，则只输出该答案。"
    '仅输出 JSON：{"stem": "题干文本", "answer": "解答文本"}；'
    "若图片中没有解答，answer 用空字符串。不要输出多余解释。"
)

# 触发「配额/限流」判定的关键字（小写后命中即视为 1003）
_QUOTA_HINTS = ("quota", "throttl", "rate limit", "limit exceeded", "too many requests")
# 触发「服务未开通/无权限/鉴权失败」判定的关键字（小写后命中即视为 1005）
_AUTH_HINTS = (
    "unauthorized",
    "invalid api key",
    "invalid_api_key",
    "invalidapikey",
    "forbidden",
    "authentication",
    "auth failed",
)


class RecognizeError(Exception):
    """带业务错误码的识别异常。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RecognizeOutcome:
    """识别结果（已清洗）。"""

    stem: str
    answer: str


def _parse_content(content: str) -> Tuple[str, str]:
    """从容错地解析模型输出中的 {stem, answer}。

    依次尝试：去除 ```json 代码块围栏 → 截取首个 JSON 对象 → json.loads。
    解析失败时把整段文本当作题干、answer 置空（容错优先，不抛错）。
    """
    text = (content or "").strip()
    if not text:
        return "", ""

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    candidate = text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]

    try:
        # strict=False：容忍模型在 JSON 字符串内直接换行（未转义）的多行解答，
        # 否则多行 answer 会导致 json.loads 失败、整段文本被误当作题干。
        parsed = json.loads(candidate, strict=False)
    except (TypeError, ValueError):
        return clean_text(content), ""

    if not isinstance(parsed, dict):
        return clean_text(content), ""

    stem = clean_text(str(parsed.get("stem", "") or ""))
    answer = clean_text(str(parsed.get("answer", "") or ""))
    return stem, answer


def _map_to_error(exc: Any) -> RecognizeError:
    """把 HTTP 响应 / 异常映射为业务错误码。"""
    status = getattr(exc, "status_code", None)
    if status == 429:
        return RecognizeError(CODE_QUOTA_EXCEEDED, "识别额度受限，请稍后再试")
    if status in (401, 403):
        return RecognizeError(
            CODE_SERVICE_UNAVAILABLE, "识别服务未开通或无权限，请检查密钥配置"
        )

    message = str(getattr(exc, "message", "") or getattr(exc, "text", "") or exc)
    haystack = message.lower()
    if any(hint in haystack for hint in _QUOTA_HINTS):
        return RecognizeError(CODE_QUOTA_EXCEEDED, "识别额度受限，请稍后再试")
    if any(hint in haystack for hint in _AUTH_HINTS):
        return RecognizeError(
            CODE_SERVICE_UNAVAILABLE, "识别服务未开通或无权限，请检查密钥配置"
        )
    return RecognizeError(CODE_RECOGNIZE_FAILED, "识别失败，请重试或手动输入")


class VisionClient:
    """OpenAI 兼容视觉端点适配器（httpx 直连，异常映射为业务错误码）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        enabled: bool = True,
        timeout: float = 20.0,
    ):
        self._api_key = api_key or ""
        self._base_url = (base_url or "").rstrip("/")
        self._model = model or "glm-4v-flash"
        self._enabled = bool(enabled)
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return self._enabled and bool(self._api_key) and bool(self._base_url)

    def recognize(
        self, image_bytes: bytes, mime_type: str = _DEFAULT_MIME
    ) -> Tuple[str, str]:
        """调用视觉模型，返回 (stem, answer)。"""
        if not self.is_configured:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务未配置访问密钥")
        if not image_bytes:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "图片为空，请重新拍摄或选择")

        import httpx

        mime = mime_type if mime_type.startswith("image/") else _DEFAULT_MIME
        data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                url, json=payload, headers=headers, timeout=self._timeout
            )
        except Exception as exc:  # noqa: BLE001 - 网络异常统一映射
            raise _map_to_error(exc) from exc

        if response.status_code != 200:
            raise _map_to_error(response)

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001 - 响应结构异常
            raise RecognizeError(
                CODE_RECOGNIZE_FAILED, "识别结果解析失败，请重试"
            ) from exc

        if isinstance(content, list):
            # 部分模型返回分段 content 数组，拼接其中的 text 片段
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        return _parse_content(str(content))


class VisionRecognizeService:
    """识别业务编排：调用视觉模型，返回题干 + 答案。"""

    def __init__(self, client: Optional[VisionClient]):
        self._client = client

    def recognize(
        self, image_bytes: bytes, mime_type: str = _DEFAULT_MIME
    ) -> RecognizeOutcome:
        if self._client is None or not self._client.is_configured:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务未配置访问密钥")
        stem, answer = self._client.recognize(image_bytes, mime_type)
        return RecognizeOutcome(stem=stem, answer=answer)
