"""变式题生成服务：调用 OpenAI 兼容文本模型，一次返回分类 + N 道同考点变式。

分层：
- GlmVariantGenerator：httpx 直连 ``{base_url}/chat/completions``（与 vision_recognize 同范式）
- DisabledVariantGenerator：AI 未启用时统一抛 9001

生成流程（避免变式照抄原题句式）：
1. 规划：只产出考点卡与 N 条互不相同的命题方案，不写题面
2. 成题：逐条方案单独调用，且提示词中不携带原题题干，去掉句式锚点
3. 门禁：与原题或彼此过于相似时，带反馈重写一次
4. 降级：规划 JSON 解析失败时回退单次生成，保证可用性

约束：变式题仅用于即时练习，不入库、不上行同步。
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, TypedDict, runtime_checkable

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
_MAX_IDEAS = 8
# 规划与成题分两次采样：规划要稳，成题要放得开
_PLAN_TEMPERATURE = 0.7
_DRAFT_TEMPERATURE = 0.9
# 考点已知时的单次命题温度：理科答案正确率优先
_SINGLE_TEMPERATURE = 0.7
_MAX_EXAM_POINT_LEN = 200
# 门禁阈值：与原题字符 3-gram 重合度、开头照抄、变式两两重合度
SIMILARITY_THRESHOLD = 0.55
OPENING_ECHO_LEN = 10
_PAIRWISE_THRESHOLD = 0.72
_DRAFT_MAX_WORKERS = 3
# 成题阶段预留规划与重写的总预算
_DRAFT_TIMEOUT_RESERVE = 8.0

_SUBJECTS = ("math", "physics", "chemistry", "other")
_QUESTION_TYPES = ("选择题", "填空题", "解答题", "证明题", "其他")
_MAX_KNOWLEDGE_POINTS = 3
_MAX_KNOWLEDGE_POINT_LEN = 32

_AXIS_LABELS = {
    "A": "情境替换",
    "B": "条件变化",
    "C": "设问反转",
    "D": "表征转换",
    "E": "结构升级",
    "F": "错误辨析",
}

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


class _VariantRequired(TypedDict):
    stem: str
    answer: str


class Variant(_VariantRequired, total=False):
    """一道变式题；axis 为变化轴标识（模型输出时可缺省）。"""

    axis: str
    axis_note: str


@dataclass(frozen=True)
class VariantIdea:
    """一条命题方案：只描述思路，不含题面。"""

    axis: str
    scenario: str
    focus: str
    entry: str


@dataclass(frozen=True)
class VariantPlan:
    """规划结果：考点卡 + 命题方案，附带未命中复用路径时的分类。"""

    exam_point: str
    invariants: List[str]
    ideas: List[VariantIdea]
    subject: str = ""
    question_type: str = ""
    knowledge_points: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VariantResult:
    """一次生成结果：分类信息 + 变式题列表（可为空）。"""

    subject: str
    question_type: str
    knowledge_points: List[str]
    variants: List[Variant]
    exam_point: str = ""


class AiError(Exception):
    """带业务错误码的 AI 异常。"""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@runtime_checkable
class VariantGenerator(Protocol):
    """变式题生成器协议。"""

    def generate(
        self,
        stem: str,
        answer: str = "",
        count: int = _DEFAULT_COUNT,
        subject: str = "",
        question_type: str = "",
        knowledge_points: Optional[List[str]] = None,
        exam_point: str = "",
    ) -> VariantResult:
        ...


def normalize_subject(value: Any) -> str:
    """学科归一化：缺失留空，非白名单归为 other。"""
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    return raw if raw in _SUBJECTS else "other"


def normalize_question_type(value: Any) -> str:
    """题型归一化：非白名单（含缺失）一律置空。"""
    question_type = str(value or "").strip()
    return question_type if question_type in _QUESTION_TYPES else ""


def normalize_knowledge_points(value: Any) -> List[str]:
    """知识点归一化：去重、单条截断 32 字、最多 3 条。"""
    points: List[str] = []
    if isinstance(value, (list, tuple)):
        for item in value:
            label = str(item or "").strip()[:_MAX_KNOWLEDGE_POINT_LEN]
            if label and label not in points:
                points.append(label)
            if len(points) >= _MAX_KNOWLEDGE_POINTS:
                break
    return points


def normalize_axis(value: Any) -> str:
    """把模型输出的变化轴（如 “C”“C 设问反转”）归一为单个大写字母。"""
    match = re.search(r"[A-Fa-f]", str(value or ""))
    return match.group(0).upper() if match else ""


def normalize_exam_point(value: Any) -> str:
    """考点归一化：折叠空白、去首尾引号、截断 200 字（与库表列宽兼容）。"""
    raw = re.sub(r"\s+", " ", str(value or "")).strip().strip("\"'“”")
    return raw[:_MAX_EXAM_POINT_LEN]


def has_reusable_meta(
    subject: str, knowledge_points: Optional[List[str]] = None
) -> bool:
    """学科已知即可复用，跳过分类环节；知识点缺失不影响复用。"""
    return bool(subject)


# ---------- 相似度门禁 ----------

_SIMILARITY_CLEAN = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")


def normalize_similarity_text(text: str) -> str:
    """去空白与标点、统一小写，作为句式相似度比较的规范文本。"""
    return _SIMILARITY_CLEAN.sub("", (text or "").lower())


def char_ngram_jaccard(left: str, right: str, size: int = 3) -> float:
    """两段文本的字符 n-gram Jaccard 相似度（0-1，越大越像）。"""
    left_text = normalize_similarity_text(left)
    right_text = normalize_similarity_text(right)
    if not left_text or not right_text:
        return 0.0
    if size < 1:
        return 0.0
    left_grams = {
        left_text[index : index + size]
        for index in range(max(0, len(left_text) - size + 1))
    }
    right_grams = {
        right_text[index : index + size]
        for index in range(max(0, len(right_text) - size + 1))
    }
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def opening_echo(
    left: str, right: str, size: int = OPENING_ECHO_LEN
) -> bool:
    """题干开头是否与原题完全相同（典型的照抄句式）。"""
    left_text = normalize_similarity_text(left)[:size]
    right_text = normalize_similarity_text(right)[:size]
    return bool(left_text) and left_text == right_text


def is_too_similar(stem: str, original: str) -> Tuple[bool, float, bool]:
    """综合判定：返回（是否过像、重合度、是否开头照抄）。"""
    score = char_ngram_jaccard(stem, original)
    echo = opening_echo(stem, original)
    return (echo or score > SIMILARITY_THRESHOLD), score, echo


# ---------- 提示词 ----------

_EXAM_POINT_CARD = (
    "第 1 步 先在内部写出考点卡（不展示给学生）：\n"
    "   - 考点：本题真正检验的可迁移能力或规律，一句话落到学生要做的动作\n"
    "   - 本质要素：缺了这些就不再考该考点（2-3 条）\n"
    "   - 可变化要素：情境、数据形式、设问方向、表征方式、条件强弱、解题链长度\n"
    "   - 解题链：拿满分必须依次完成的 2-4 个关键判断\n"
    "   - 典型错误：该考点最常见的 1-2 个错误\n\n"
)


def _variation_brief(count: int, include_meta: bool = False) -> str:
    """变化轴配额与自检要求：把“根据考点命题”拆成可执行约束。"""
    axis_floor = min(count, 3)
    if include_meta:
        head = (
            '{"subject": "math", "questionType": "解答题", '
            '"knowledgePoints": ["知识点1"], "examPoint": "考点", '
        )
    else:
        head = '{"examPoint": "考点", '
    return (
        "第 2 步 为每道变式分配不同的变化轴，同一轴最多使用一次：\n"
        "   A 情境替换：换一个真实或学科情境，解题链不变\n"
        "   B 条件变化：增删、弱化或强化一个条件，考点不变\n"
        "   C 设问反转：条件与结论互换，或由求值改为求范围、证存在、举反例\n"
        "   D 表征转换：文字、表格、图像、公式之间换一种呈现同一关系\n"
        "   E 结构升级：在原题基础上增加一问，形成递进\n"
        "   F 错误辨析：给出一个有典型错误的解法，让学生判断并纠正\n"
        f"   按学科取舍，{count} 道题至少覆盖 {axis_floor} 个不同轴。\n\n"
        "第 3 步 逐题自检后再输出：\n"
        "   - 考点一致：不引入原题未涉及的新知识点，难度不超过原题一档\n"
        "   - 句式独立：不得沿用原题的句式框架，不得只替换数字、人名、单位\n"
        "   - 题目互异：任意两道变式之间，情境、设问、解题入口至少两项不同\n"
        "   - 答案可靠：独立求解一遍，可验算的必须验算\n\n"
        "输出格式："
        f"{head}"
        '"variants": [{"axis": "C", "axisNote": "一句话说明变了什么", '
        '"stem": "...", "answer": "..."}]}\n'
        "只输出 JSON，不要解释。"
    )


def _build_prompt(stem: str, answer: str, count: int) -> str:
    return (
        "你是一名命题教师。下面是一道学生的错题。\n"
        "你的任务不是改写这道题，而是围绕同一个考点重新命题。\n\n"
        f"【题目】\n{stem}\n\n"
        f"【答案/解答】\n{answer or '（未提供）'}\n\n"
        "先识别以下信息并随结果输出：\n"
        "   - 学科（math/physics/chemistry/other）\n"
        "   - 题型（选择题/填空题/解答题/证明题/其他）\n"
        "   - 1-3 个知识点标签（简短关键词）\n\n"
        f"{_EXAM_POINT_CARD}"
        f"{_variation_brief(count, include_meta=True)}"
    )


def _build_reuse_prompt(
    stem: str,
    answer: str,
    count: int,
    subject: str,
    question_type: str,
    knowledge_points: List[str],
    exam_point: str = "",
) -> str:
    """分类已知时只生成变式，跳过重新分类，复用库内元信息（含考点）。"""
    points_label = "、".join(knowledge_points) or "未提供"
    exam_section = (
        f"【考点】{exam_point}\n"
        "（本题考点已确定，不得替换为相邻考点；所有变式必须围绕它命题。）\n\n"
        if exam_point
        else ""
    )
    return (
        "你是一名命题教师。下面是一道学生的错题。\n"
        "你的任务不是改写这道题，而是围绕同一个考点重新命题。\n\n"
        f"【题目】（仅供理解考点与难度，严禁照抄句式）\n{stem}\n\n"
        f"【答案/解答】\n{answer or '（未提供）'}\n\n"
        f"【已知分类】学科：{subject}；题型：{question_type or '未知'}；"
        f"知识点：{points_label}\n\n"
        f"{exam_section}"
        f"{_EXAM_POINT_CARD}"
        f"{_variation_brief(count)}"
    )


def _build_plan_prompt(
    stem: str,
    answer: str,
    count: int,
    subject: str,
    question_type: str,
    knowledge_points: List[str],
) -> str:
    """规划阶段：只输出考点卡与命题方案，明确禁止写题面。"""
    idea_count = max(count, min(count * 2, _MAX_IDEAS))
    meta_section = ""
    meta_output = ""
    if subject:
        points_label = "、".join(knowledge_points) or "未提供"
        meta_section = (
            f"【已知分类】学科：{subject}；题型：{question_type or '未知'}；"
            f"知识点：{points_label}\n\n"
        )
    else:
        meta_section = (
            "请同时判断：学科（math/physics/chemistry/other）、"
            "题型（选择题/填空题/解答题/证明题/其他）、1-3 个知识点标签。\n\n"
        )
        meta_output = (
            '"subject": "math", "questionType": "解答题", '
            '"knowledgePoints": ["知识点1"], '
        )
    return (
        "你是一名命题规划师。你的任务是为同一个考点设计互不相同的命题方案，"
        "这一阶段只写方案，不写题目正文。\n\n"
        f"【原题】\n{stem}\n\n"
        f"【参考答案】\n{answer or '（未提供）'}\n\n"
        f"{meta_section}"
        "第 1 步 提炼考点卡：\n"
        "   - 考点：本题真正检验的可迁移能力或规律\n"
        "   - 本质要素：缺了这些就不再考该考点（2-3 条）\n"
        "   - 解题链：拿满分必须依次完成的 2-4 个关键判断\n"
        "   - 典型错误：该考点最常见的 1-2 个错误\n\n"
        f"第 2 步 设计 {idea_count} 个命题方案，每个方案绑定一个变化轴，轴不得重复：\n"
        "   A 情境替换：换一个真实或学科情境，解题链不变\n"
        "   B 条件变化：增删、弱化或强化一个条件，考点不变\n"
        "   C 设问反转：条件与结论互换，或由求值改为求范围、证存在、举反例\n"
        "   D 表征转换：文字、表格、图像、公式之间换一种呈现同一关系\n"
        "   E 结构升级：在原题基础上增加一问，形成递进\n"
        "   F 错误辨析：设计一个含典型错误的解法，让学生判断并纠正\n"
        "   每个方案只写思路，不写题面：\n"
        "   - scenario：情境或表征方式\n"
        "   - focus：这道题要检验的具体动作\n"
        "   - entry：解题入口，必须与原题不同\n\n"
        "输出格式（严禁输出题目正文）：\n"
        "{" + meta_output
        + '"examPoint": "考点", "invariants": ["本质要素"], '
        '"ideas": [{"axis": "A", "scenario": "...", "focus": "...", "entry": "..."}]}\n'
        "只输出 JSON，不要解释。"
    )


def _build_draft_prompt(
    plan: VariantPlan,
    idea: VariantIdea,
    subject: str,
    question_type: str,
    knowledge_points: List[str],
    feedback: str = "",
) -> str:
    """成题阶段：只给考点与单条方案，不携带原题，避免句式锚定。"""
    points_label = "、".join(knowledge_points) or "未指定"
    invariants = "；".join(plan.invariants) or "（无）"
    axis_label = _AXIS_LABELS.get(idea.axis, idea.axis)
    feedback_section = f"\n{feedback}\n" if feedback else ""
    return (
        "请根据下面的命题方案独立写出 1 道完整的"
        f"{question_type or '题目'}，学科：{subject or '未指定'}，"
        f"知识点：{points_label}。\n\n"
        f"【考点】{plan.exam_point}\n"
        f"【必须保持不变】{invariants}\n\n"
        "【本题设计】\n"
        f"   - 变化轴：{idea.axis} {axis_label}\n"
        f"   - 情境/表征：{idea.scenario}\n"
        f"   - 检验动作：{idea.focus}\n"
        f"   - 解题入口：{idea.entry}\n"
        f"{feedback_section}\n"
        "要求：\n"
        "   1. 题干自洽完整，学生不看原题也能作答\n"
        "   2. 不要套用固定题面模板，开头与设问方式要符合所选变化轴\n"
        "   3. 不引入新的知识点，难度与原题相当\n"
        "   4. 给出完整答案；输出前独立求解并验算\n\n"
        '输出 JSON：{"stem": "...", "answer": "..."}\n'
        "只输出 JSON，不要解释。"
    )


# ---------- 解析 ----------


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """从模型输出中截取首个 JSON 对象，容忍代码围栏与前后说明。"""
    raw = (text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S)
    if fence:
        raw = fence.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(raw[start : end + 1], strict=False)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _parse_plan(content: str, count: int) -> Optional[VariantPlan]:
    """解析规划 JSON；结构不可用时返回 None 以触发单次生成降级。"""
    parsed = _extract_json_object(content)
    if not parsed:
        return None
    exam_point = str(parsed.get("examPoint") or parsed.get("exam_point") or "").strip()
    if not exam_point:
        return None

    raw_invariants = parsed.get("invariants")
    invariants: List[str] = []
    if isinstance(raw_invariants, list):
        for item in raw_invariants:
            label = str(item or "").strip()
            if label:
                invariants.append(label)
            if len(invariants) >= 4:
                break

    raw_ideas = parsed.get("ideas")
    if not isinstance(raw_ideas, list):
        return None

    ideas: List[VariantIdea] = []
    used_axes: set = set()
    for item in raw_ideas:
        if not isinstance(item, dict):
            continue
        axis = normalize_axis(item.get("axis"))
        scenario = str(item.get("scenario") or "").strip()
        if not axis or not scenario or axis in used_axes:
            continue
        used_axes.add(axis)
        ideas.append(
            VariantIdea(
                axis=axis,
                scenario=scenario,
                focus=str(item.get("focus") or "").strip(),
                entry=str(item.get("entry") or "").strip(),
            )
        )
        if len(ideas) >= max(count, min(count * 2, _MAX_IDEAS)):
            break
    if not ideas:
        return None

    return VariantPlan(
        exam_point=exam_point,
        invariants=invariants,
        ideas=ideas,
        subject=normalize_subject(parsed.get("subject")),
        question_type=normalize_question_type(
            parsed.get("questionType") or parsed.get("question_type")
        ),
        knowledge_points=normalize_knowledge_points(
            parsed.get("knowledgePoints") or parsed.get("knowledge_points")
        ),
    )


def _parse_variant(content: str) -> Variant:
    """解析单条成题结果，兼容被包在 variants 数组里的写法。"""
    parsed = _extract_json_object(content)
    if not parsed:
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")
    if isinstance(parsed.get("variants"), list) and parsed["variants"]:
        first = parsed["variants"][0]
        if isinstance(first, dict):
            parsed = first
    stem = str(parsed.get("stem") or "").strip()
    if not stem:
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")
    variant: Variant = {
        "stem": stem,
        "answer": str(parsed.get("answer") or "").strip(),
    }
    axis = normalize_axis(parsed.get("axis"))
    if axis:
        variant["axis"] = axis
    axis_note = str(parsed.get("axisNote") or parsed.get("axis_note") or "").strip()
    if axis_note:
        variant["axis_note"] = axis_note
    return variant


def _parse_result(content: str, count: int) -> VariantResult:
    """容错解析模型输出。

    依次尝试：去除 ```json 围栏 → 截取首个 JSON 对象 → json.loads(strict=False)。
    解析失败抛 9004；``variants`` 缺失答案时以空字符串兜底；空列表视为合法空结果。
    """
    text = (content or "").strip()
    if not text:
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")

    parsed = _extract_json_object(text)
    if not parsed:
        logger.warning("ai variants parse failed: %s", str(content)[:200])
        raise AiError(CODE_AI_PARSE_FAILED, "生成失败，换一道题试试")

    subject = normalize_subject(parsed.get("subject")) or "other"
    question_type = normalize_question_type(
        parsed.get("questionType") or parsed.get("question_type")
    )
    points = normalize_knowledge_points(
        parsed.get("knowledgePoints") or parsed.get("knowledge_points")
    )

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
        variant: Variant = {
            "stem": stem,
            "answer": str(item.get("answer") or "").strip(),
        }
        axis = normalize_axis(item.get("axis"))
        if axis:
            variant["axis"] = axis
        axis_note = str(item.get("axisNote") or item.get("axis_note") or "").strip()
        if axis_note:
            variant["axis_note"] = axis_note
        variants.append(variant)
        if len(variants) >= count:
            break

    return VariantResult(
        subject=subject,
        question_type=question_type,
        knowledge_points=points,
        variants=variants,
        exam_point=str(parsed.get("examPoint") or "").strip(),
    )


def _select_ideas(
    plan: VariantPlan, count: int
) -> Tuple[List[VariantIdea], List[VariantIdea]]:
    """按轴去重挑选 count 条方案，返回（选中, 备用）。"""
    picked: List[VariantIdea] = []
    used_axes: set = set()
    for idea in plan.ideas:
        if idea.axis in used_axes:
            continue
        used_axes.add(idea.axis)
        picked.append(idea)
        if len(picked) >= count:
            break

    spare = [idea for idea in plan.ideas if idea not in picked]
    if len(picked) < count:
        picked.extend(spare[: count - len(picked)])
        spare = spare[count - len(picked) :]
    return picked, spare


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

    @property
    def model(self) -> str:
        """当前生效的模型名（供启动/请求日志确认实际调用）。"""
        return self._model

    def _chat(self, prompt: str, temperature: float, timeout: float) -> str:
        """单次对话请求，返回模型文本内容（异常统一映射为业务错误码）。"""
        if not self.is_configured:
            raise AiError(CODE_AI_UNAVAILABLE, "AI 服务暂不可用，请稍后再试")

        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=timeout)
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
        return str(body or "")

    def _draft_timeout(self) -> float:
        return max(6.0, float(self._timeout) - _DRAFT_TIMEOUT_RESERVE)

    def _generate_single(
        self,
        stem: str,
        answer: str,
        limit: int,
        known_subject: str,
        known_type: str,
        known_points: List[str],
        reuse_meta: bool,
        exam_point: str = "",
    ) -> VariantResult:
        """单次生成：考点已知时的主路径（规划不可用时的降级路径）。"""
        prompt = (
            _build_reuse_prompt(
                stem, answer, limit, known_subject, known_type, known_points, exam_point
            )
            if reuse_meta
            else _build_prompt(stem, answer, limit)
        )
        temperature = _SINGLE_TEMPERATURE if exam_point else _DRAFT_TEMPERATURE
        body = self._chat(prompt, temperature, self._timeout)
        result = _parse_result(body, limit)
        if not reuse_meta:
            return result
        return VariantResult(
            subject=known_subject,
            question_type=known_type,
            knowledge_points=known_points,
            variants=result.variants,
            exam_point=exam_point or result.exam_point,
        )

    def _draft_one(
        self,
        original: str,
        plan: VariantPlan,
        idea: VariantIdea,
        subject: str,
        question_type: str,
        points: List[str],
    ) -> Variant:
        """按单条方案成题；与原题过像时带反馈重写一次。"""
        prompt = _build_draft_prompt(plan, idea, subject, question_type, points)
        variant = _parse_variant(
            self._chat(prompt, _DRAFT_TEMPERATURE, self._draft_timeout())
        )
        too_similar, score, echo = is_too_similar(variant["stem"], original)
        if not too_similar:
            variant["axis"] = idea.axis
            return variant

        hint = "开头与原文相同" if echo else f"与原题重合度 {score:.2f}"
        feedback = (
            f"上一版{hint}（阈值 {SIMILARITY_THRESHOLD:.2f}，开头 {OPENING_ECHO_LEN} 字"
            "相同即视为照抄）。请彻底更换开头表述与设问结构后重写同一道题。"
        )
        retry_prompt = _build_draft_prompt(
            plan, idea, subject, question_type, points, feedback=feedback
        )
        retry = _parse_variant(
            self._chat(retry_prompt, _DRAFT_TEMPERATURE, self._draft_timeout())
        )
        retry_too_similar, retry_score, retry_echo = is_too_similar(
            retry["stem"], original
        )
        # 重写仍不达标时保留更像“新题”的那一版
        if not retry_too_similar or retry_score < score or (echo and not retry_echo):
            variant = retry
        variant["axis"] = idea.axis
        return variant

    def _draft_variants(
        self,
        original: str,
        plan: VariantPlan,
        ideas: List[VariantIdea],
        spare: List[VariantIdea],
        subject: str,
        question_type: str,
        points: List[str],
    ) -> List[Variant]:
        """并行成题，并做变式两两去重。"""
        drafted: List[Variant] = []
        with ThreadPoolExecutor(
            max_workers=max(1, min(len(ideas), _DRAFT_MAX_WORKERS))
        ) as pool:
            futures = [
                pool.submit(
                    self._draft_one,
                    original,
                    plan,
                    idea,
                    subject,
                    question_type,
                    points,
                )
                for idea in ideas
            ]
            for idea, future in zip(ideas, futures):
                try:
                    drafted.append(future.result())
                except AiError as exc:
                    logger.warning("ai draft failed axis=%s: %s", idea.axis, exc.message)

        # 变式之间过像：用备用方案重写后一条一次
        for index in range(1, len(drafted)):
            duplicated = any(
                char_ngram_jaccard(drafted[index]["stem"], previous["stem"])
                > _PAIRWISE_THRESHOLD
                for previous in drafted[:index]
            )
            if not duplicated or not spare:
                continue
            replacement_idea = spare.pop(0)
            try:
                drafted[index] = self._draft_one(
                    original,
                    plan,
                    replacement_idea,
                    subject,
                    question_type,
                    points,
                )
            except AiError as exc:
                logger.warning(
                    "ai dedupe rewrite failed axis=%s: %s",
                    replacement_idea.axis,
                    exc.message,
                )
        return drafted

    def generate(
        self,
        stem: str,
        answer: str = "",
        count: int = _DEFAULT_COUNT,
        subject: str = "",
        question_type: str = "",
        knowledge_points: Optional[List[str]] = None,
        exam_point: str = "",
    ) -> VariantResult:
        content = (stem or "").strip()
        if not content:
            raise AiError(CODE_AI_PARSE_FAILED, "题目内容为空，无法生成")
        if not self.is_configured:
            raise AiError(CODE_AI_UNAVAILABLE, "AI 服务暂不可用，请稍后再试")

        try:
            limit = int(count or _DEFAULT_COUNT)
        except (TypeError, ValueError):
            limit = _DEFAULT_COUNT
        limit = max(1, min(limit, _MAX_COUNT))

        known_subject = normalize_subject(subject)
        known_type = normalize_question_type(question_type)
        known_points = normalize_knowledge_points(knowledge_points)
        reuse_meta = has_reusable_meta(known_subject, known_points)

        # 考点已知（识别阶段已落库）：按「原题 + 题型 + 考点」单次命题，跳过规划
        known_exam_point = normalize_exam_point(exam_point)
        if known_exam_point:
            return self._generate_single(
                content,
                answer,
                limit,
                known_subject,
                known_type,
                known_points,
                reuse_meta=True,
                exam_point=known_exam_point,
            )

        fallback_subject = known_subject or "other"

        # 阶段 1：规划（只出方案，不出题面）
        plan: Optional[VariantPlan] = None
        try:
            plan_prompt = _build_plan_prompt(
                content,
                answer,
                limit,
                known_subject,
                known_type,
                known_points,
            )
            plan = _parse_plan(
                self._chat(plan_prompt, _PLAN_TEMPERATURE, self._draft_timeout()),
                limit,
            )
        except AiError as exc:
            if exc.code != CODE_AI_PARSE_FAILED:
                raise
            logger.warning("ai plan parse failed, fallback to single pass")

        if plan is None:
            return self._generate_single(
                content,
                answer,
                limit,
                known_subject,
                known_type,
                known_points,
                reuse_meta,
            )

        if reuse_meta:
            subject_out = known_subject
            type_out = known_type
            points_out = known_points
        else:
            subject_out = plan.subject or fallback_subject
            type_out = plan.question_type
            points_out = plan.knowledge_points

        # 阶段 2：按轴选方案，逐条并行成题
        ideas, spare = _select_ideas(plan, limit)
        if not ideas:
            return self._generate_single(
                content,
                answer,
                limit,
                known_subject,
                known_type,
                known_points,
                reuse_meta,
            )

        variants = self._draft_variants(
            content,
            plan,
            ideas,
            spare,
            subject_out,
            type_out,
            points_out,
        )
        if not variants:
            raise AiError(CODE_AI_UPSTREAM_BUSY, "生成失败，请换一道题试试")

        return VariantResult(
            subject=subject_out,
            question_type=type_out,
            knowledge_points=points_out,
            variants=variants[:limit],
            exam_point=plan.exam_point,
        )


class DisabledVariantGenerator:
    """默认实现：AI 未启用，统一返回 9001。"""

    def generate(
        self,
        stem: str,
        answer: str = "",
        count: int = _DEFAULT_COUNT,
        subject: str = "",
        question_type: str = "",
        knowledge_points: Optional[List[str]] = None,
        exam_point: str = "",
    ) -> VariantResult:
        raise AiError(CODE_AI_NOT_ENABLED, "AI 功能暂未开放")
