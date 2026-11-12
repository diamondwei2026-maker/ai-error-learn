"""变式题生成服务：调用 OpenAI 兼容文本模型，一次返回分类 + N 道同构变式。

分层：
- GlmVariantGenerator：httpx 直连 ``{base_url}/chat/completions``（与 vision_recognize 同范式）
- DisabledVariantGenerator：AI 未启用时统一抛 9001

约束：变式题仅用于即时练习，不入库、不上行同步。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, TypedDict, runtime_checkable

import httpx

logger = logging.getLogger(__name__)

# 业务错误码（与前端 AI_ERROR_MESSAGES 对齐）
CODE_AI_NOT_ENABLED = 9001
CODE_AI_UPSTREAM_BUSY = 9002
CODE_AI_UNAVAILABLE = 9003
CODE_AI_PARSE_FAILED = 9004
CODE_AI_CONTENT_RISKY = 9005
CODE_AI_RATE_LIMITED = 9006

_DEFAULT_COUNT = 3
_MAX_COUNT = 5
_SUBJECTS = ("math", "physics", "chemistry", "other")

# 触发「额度/限流」判定的关键字（小写后命中即视为 9002）
_QUOTA_HINTS = ("quota", "throttl", "rate limit", "limit exceeded", "too many requests")
# 触发「配置类不可用」判定的关键字（小写后命中即视为 9003）
_AUTH_HINTS = (
    "unauthorized",
    "invalid api key",
    "invalid_api_key",
    "invalidapikey",
    "forbidden",
    "authentication",
    "auth failed",
)


class Variant(TypedDict):
    stem: str
    answer: str


@dataclass(frozen=True)
class VariantResult:
    """一次生成结果：分类信息 + 变式题列表（可为空）。"""

    subject: str
    question_type: str
    knowledge_points: List[str]
    variants: List[Variant]


class AiError(Exception):
    """带业务错误码的 AI 异常。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@runtime_checkable
class VariantGenerator(Protocol):
    """变式题生成器协议。"""

    def generate(self, stem: str, answer: str = "", count: int = _DEFAULT_COUNT) -> VariantResult:
        ...


def _build_prompt(stem: str, answer: str, count: int) -> str:
    return (
        "你是一名经验丰富的教师助手。下面是一道学生的错题：\n\n"
        f"【题目】\n{stem}\n\n"
        f"【答案/解答】\n{answer or '（未提供）'}\n\n"
        "请完成以下任务，仅输出 JSON：\n"
        "1. 识别这道题的学科（math/physics/chemistry/other）\n"
        "2. 识别这道题的题型（选择题/填空题/解答题/证明题/其他）\n"
        "3. 提取 1-3 个知识点标签（简短关键词）\n"
        f"4. 生成 {count} 道【同构变式题】：\n"
        "   - 保持与原题完全相同的题型和知识点\n"
        "   - 改变具体数值、表述方式或情境，但考点不变\n"
        "   - 每道题必须提供完整答案，输出前先自检答案正确性\n"
        "   - 避免与原题过于相似（只改一个数字不算变式）\n\n"
        "输出格式："
        '{"subject": "math", "questionType": "解答题", '
        '"knowledgePoints": ["知识点1", "知识点2"], '
        '"variants": [{"stem": "...", "answer": "..."}]}\n'
        "不要输出 JSON 之外的解释。"
    )


def _map_to_error(exc: Any) -> AiError:
    """把 HTTP 响应 / 网络异常映射为业务错误码。"""
    if isinstance(exc, httpx.TimeoutException):
        return AiError(CODE_AI_UPSTREAM_BUSY, "生成超时，请重试")
    if isinstance(exc, httpx.TransportError):
        return AiError(CODE_AI_UPSTREAM_BUSY, "AI 服务连接失败，请检查网络")

    status = getattr(exc, "status_code", None)
    if status == 429:
        return AiError(CODE_AI_UPSTREAM_BUSY, "AI 太忙了，请稍后再试")
    if status in (401, 403, 400, 404, 422):
        # 鉴权失败 / 模型名不存在 / 请求参数不被上游接受：配置类错误
        return AiError(CODE_AI_UNAVAILABLE, "AI 服务暂不可用，请稍后再试")
    if isinstance(status, int) and 500 <= status < 600:
        return AiError(CODE_AI_UPSTREAM_BUSY, "AI 太忙了，请稍后再试")

    message = str(getattr(exc, "message", "") or getattr(exc, "text", "") or exc)
    haystack = message.lower()
    if any(hint in haystack for hint in _QUOTA_HINTS):
        return AiError(CODE_AI_UPSTREAM_BUSY, "AI 太忙了，请稍后再试")
    if any(hint in haystack for hint in _AUTH_HINTS):
        return AiError(CODE_AI_UNAVAILABLE, "AI 服务暂不可用，请稍后再试")
    return AiError(CODE_AI_UPSTREAM_BUSY, "生成失败，请换一道题试试")


def _parse_result(content: str, count: int) -> VariantResult:
    """容错解析模型输出。

    依次尝试：去除 ```json 围栏 → 截取首个 JSON 对象 → json.loads(strict=False)。
    解析失败抛 9004；``variants`` 缺失答案时以空字符串兜底；空列表视为合法空结果。
    """
    text = (content or "").strip()
    if not text:
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()

    candidate = text
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidate = text[start : end + 1]

    try:
        # strict=False：容忍字符串内未转义的换行（多行答案）
        parsed = json.loads(candidate, strict=False)
    except (TypeError, ValueError) as exc:
        logger.warning("ai variants parse failed: %s", str(content)[:200])
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试") from exc

    if not isinstance(parsed, dict):
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")

    subject = str(parsed.get("subject") or "other").strip().lower()
    if subject not in _SUBJECTS:
        subject = "other"
    question_type = str(
        parsed.get("questionType") or parsed.get("question_type") or ""
    ).strip()

    raw_points = parsed.get("knowledgePoints") or parsed.get("knowledge_points") or []
    points: List[str] = []
    if isinstance(raw_points, list):
        for item in raw_points:
            label = str(item or "").strip()
            if label and label not in points:
                points.append(label)
            if len(points) >= 3:
                break

    raw_variants = parsed.get("variants")
    if not isinstance(raw_variants, list):
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")

    variants: List[Variant] = []
    for item in raw_variants:
        if not isinstance(item, dict):
            continue
        stem = str(item.get("stem") or "").strip()
        if not stem:
            continue
        variants.append(
            {"stem": stem, "answer": str(item.get("answer") or "").strip()}
        )
        if len(variants) >= count:
            break

    return VariantResult(
        subject=subject,
        question_type=question_type,
        knowledge_points=points,
        variants=variants,
    )


class GlmVariantGenerator:
    """OpenAI 兼容文本端点适配器（httpx 直连，异常映射为业务错误码）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        enabled: bool = True,
        timeout: float = 30.0,
    ):
        self._api_key = api_key or ""
        self._base_url = (base_url or "").rstrip("/")
        self._model = model or "glm-4-flash"
        self._enabled = bool(enabled)
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return self._enabled and bool(self._api_key) and bool(self._base_url)

    def generate(
        self, stem: str, answer: str = "", count: int = _DEFAULT_COUNT
    ) -> VariantResult:
        if not self.is_configured:
            raise AiError(CODE_AI_UNAVAILABLE, "AI 服务暂不可用，请稍后再试")

        content = (stem or "").strip()
        if not content:
            raise AiError(CODE_AI_PARSE_FAILED, "题目内容为空，无法生成")

        try:
            limit = int(count or _DEFAULT_COUNT)
        except (TypeError, ValueError):
            limit = _DEFAULT_COUNT
        limit = max(1, min(limit, _MAX_COUNT))

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "temperature": 0.3,
            "messages": [
                {"role": "user", "content": _build_prompt(content, answer, limit)}
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
            logger.warning("ai upstream exception: %s: %s", type(exc).__name__, exc)
            raise _map_to_error(exc) from exc

        if response.status_code != 200:
            logger.warning(
                "ai upstream non-200: status=%s body=%s",
                response.status_code,
                (getattr(response, "text", "") or "")[:300],
            )
            raise _map_to_error(response)

        try:
            body = response.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001 - 响应结构异常
            raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试") from exc

        if isinstance(body, list):
            # 部分模型返回分段 content 数组，拼接其中的 text 片段
            body = "".join(
                part.get("text", "") for part in body if isinstance(part, dict)
            )
        return _parse_result(str(body), limit)


class DisabledVariantGenerator:
    """默认实现：AI 未启用，统一返回 9001。"""

    def generate(
        self, stem: str, answer: str = "", count: int = _DEFAULT_COUNT
    ) -> VariantResult:
        raise AiError(CODE_AI_NOT_ENABLED, "AI 功能暂未开放")
