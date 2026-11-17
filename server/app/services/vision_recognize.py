"""多模态识别服务：调用轻量级视觉大模型一步识别题干与完整解答（含解题过程）。

分层：
- VisionClient：OpenAI 兼容（/chat/completions）视觉端点适配器（httpx，无新增依赖）
- VisionRecognizeService：业务编排，把调用异常映射为业务错误码

测试阶段使用 GLM-4V-Flash，上线切换为 Qwen-VL-Flash，均通过配置切换，无需改代码。
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import httpx

from app.utils.text_clean import clean_text

logger = logging.getLogger(__name__)

# 业务错误码（沿用原数值，前端文案无需改码）
CODE_RECOGNIZE_FAILED = 1002
CODE_QUOTA_EXCEEDED = 1003
CODE_IMAGE_TOO_LARGE = 1004
CODE_SERVICE_UNAVAILABLE = 1005  # 服务未开通 / 无权限 / 鉴权失败

_DEFAULT_MIME = "image/jpeg"

# 识别 + 拆题提示词：约束模型只输出题干、完整解答与元信息 JSON（解答需保留解题过程）
_PROMPT = (
    "你是题目识别助手。请识别图片中的题目内容，并拆分为「题干」与「解答」两部分。"
    "其中「解答」需完整保留图片中给出的解题过程（含每一步推导、计算与最终结论），"
    "按原有顺序与换行输出，不要只提取最终答案；若图片只有最终答案，则只输出该答案。"
    "另外请判断题目元信息：学科 subject（math/physics/chemistry/other，无法判断填 other）、"
    "题型 questionType（选择题/填空题/解答题/证明题/其他，无法判断填空字符串）、"
    "考点 examPoint（一句话，说明本题真正考查的可迁移能力或规律，"
    "如“二次函数在闭区间上的最值”，无法判断填空字符串）、"
    "知识点 knowledgePoints（1-3 个简短关键词数组，无法判断填空数组）。"
    '仅输出 JSON：{"stem": "题干文本", "answer": "解答文本", "subject": "math", '
    '"questionType": "解答题", "examPoint": "考点", "knowledgePoints": ["知识点1", "知识点2"]}；'
    "若图片中没有解答，answer 用空字符串。不要输出多余解释。"
)

# 元信息白名单与上限（与前端 constants / 同步接口保持一致）
_SUBJECTS = ("math", "physics", "chemistry", "other")
_QUESTION_TYPES = ("选择题", "填空题", "解答题", "证明题", "其他")
# 视觉模型常见的题型近义词：先映射再走白名单，避免因措辞差异把题型丢空
_QUESTION_TYPE_ALIASES = {
    "单选题": "选择题",
    "多选题": "选择题",
    "选择": "选择题",
    "填空": "填空题",
    "计算题": "解答题",
    "应用题": "解答题",
    "解答": "解答题",
    "证明": "证明题",
}
_MAX_KNOWLEDGE_POINTS = 3
_MAX_KNOWLEDGE_POINT_LEN = 32
_MAX_EXAM_POINT_LEN = 200

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
    """识别结果（已清洗）。元信息缺省为空，保证旧调用方无感。"""

    stem: str
    answer: str
    subject: str = ""
    question_type: str = ""
    knowledge_points: Tuple[str, ...] = ()
    exam_point: str = ""


def normalize_subject(value: Any) -> str:
    """学科归一化：缺失留空，非白名单归为 other。"""
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    return raw if raw in _SUBJECTS else "other"


def normalize_question_type(value: Any) -> str:
    """题型归一化：先做常见同义词映射，非白名单（含缺失）一律置空。"""
    question_type = str(value or "").strip()
    question_type = _QUESTION_TYPE_ALIASES.get(question_type, question_type)
    return question_type if question_type in _QUESTION_TYPES else ""


def normalize_exam_point(value: Any) -> str:
    """考点归一化：折叠空白、去首尾引号、截断 200 字（与库表列宽兼容）。"""
    raw = re.sub(r"\s+", " ", str(value or "")).strip().strip("\"'“”")
    return raw[:_MAX_EXAM_POINT_LEN]


def normalize_knowledge_points(value: Any) -> Tuple[str, ...]:
    """知识点归一化：去重、单条截断 32 字、最多 3 条。"""
    points: list[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            label = str(item or "").strip()[:_MAX_KNOWLEDGE_POINT_LEN]
            if label and label not in points:
                points.append(label)
            if len(points) >= _MAX_KNOWLEDGE_POINTS:
                break
    return tuple(points)


def _parse_content(content: str) -> Tuple[str, str, str, str, str, Tuple[str, ...]]:
    """从容错地解析模型输出中的 {stem, answer, subject, questionType, examPoint, knowledgePoints}。

    依次尝试：去除 ```json 代码块围栏 → 截取首个 JSON 对象 → json.loads。
    解析失败时把整段文本当作题干、answer 置空、元信息留空（容错优先，不抛错）。
    """
    text = (content or "").strip()
    if not text:
        return "", "", "", "", "", ()

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
        return clean_text(content), "", "", "", "", ()

    if not isinstance(parsed, dict):
        return clean_text(content), "", "", "", "", ()

    stem = clean_text(str(parsed.get("stem", "") or ""))
    answer = clean_text(str(parsed.get("answer", "") or ""))
    subject = normalize_subject(parsed.get("subject"))
    question_type = normalize_question_type(
        parsed.get("questionType") or parsed.get("question_type")
    )
    exam_point = normalize_exam_point(
        parsed.get("examPoint") or parsed.get("exam_point")
    )
    points = normalize_knowledge_points(
        parsed.get("knowledgePoints") or parsed.get("knowledge_points")
    )
    return stem, answer, subject, question_type, exam_point, points


def _map_to_error(exc: Any) -> RecognizeError:
    """把 HTTP 响应 / 异常映射为业务错误码。"""
    status = getattr(exc, "status_code", None)
    if status == 429:
        return RecognizeError(CODE_QUOTA_EXCEEDED, "识别额度受限，请稍后再试")
    if status in (401, 403):
        return RecognizeError(
            CODE_SERVICE_UNAVAILABLE, "识别服务未开通或无权限，请检查密钥配置"
        )
    if status in (400, 404, 422):
        # 模型名不存在 / 请求参数不被上游接受：属配置类错误，明确指向 VISION_MODEL
        return RecognizeError(
            CODE_SERVICE_UNAVAILABLE, "识别模型不可用，请检查 VISION_MODEL 配置"
        )
    if isinstance(status, int) and 500 <= status < 600:
        return RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务暂时不可用，请稍后重试")

    if isinstance(exc, httpx.TimeoutException):
        return RecognizeError(CODE_RECOGNIZE_FAILED, "识别超时，请重试")
    if isinstance(exc, httpx.TransportError):
        return RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务连接失败，请检查网络")

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

    def recognize_full(
        self, image_bytes: bytes, mime_type: str = _DEFAULT_MIME
    ) -> Tuple[str, str, str, str, str, Tuple[str, ...]]:
        """调用视觉模型，返回 (stem, answer, subject, question_type, exam_point, knowledge_points)。"""
        if not self.is_configured:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务未配置访问密钥")
        if not image_bytes:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "图片为空，请重新拍摄或选择")

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
            logger.warning(
                "vision upstream exception: %s: %s", type(exc).__name__, exc
            )
            raise _map_to_error(exc) from exc

        if response.status_code != 200:
            logger.warning(
                "vision upstream non-200: status=%s body=%s",
                response.status_code,
                (getattr(response, "text", "") or "")[:300],
            )
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

    def recognize(
        self, image_bytes: bytes, mime_type: str = _DEFAULT_MIME
    ) -> Tuple[str, str]:
        """兼容旧调用：仅返回 (stem, answer)。"""
        stem, answer, _subject, _question_type, _exam_point, _points = (
            self.recognize_full(image_bytes, mime_type)
        )
        return stem, answer


class VisionRecognizeService:
    """识别业务编排：调用视觉模型，返回题干 + 答案 + 元信息。"""

    def __init__(self, client: Optional[VisionClient]):
        self._client = client

    def recognize(
        self, image_bytes: bytes, mime_type: str = _DEFAULT_MIME
    ) -> RecognizeOutcome:
        if self._client is None or not self._client.is_configured:
            raise RecognizeError(CODE_RECOGNIZE_FAILED, "识别服务未配置访问密钥")
        stem, answer, subject, question_type, exam_point, points = (
            self._client.recognize_full(image_bytes, mime_type)
        )
        logger.info(
            "recognize meta: subject=%s type=%s points=%s exam_point=%s",
            subject or "-",
            question_type or "-",
            len(points),
            bool(exam_point),
        )
        return RecognizeOutcome(
            stem=stem,
            answer=answer,
            subject=subject,
            question_type=question_type,
            knowledge_points=points,
            exam_point=exam_point,
        )
