"""AI 举一反三接口：根据错题生成同构变式题（不入库、不排期）。"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, Request

from app.config import get_current_settings
from app.errors import CODE_PARAM_INVALID, ApiError
from app.models.question_sync import QuestionSync
from app.services.ai_service import (
    CODE_AI_CONTENT_RISKY,
    CODE_AI_RATE_LIMITED,
    CODE_AI_UPSTREAM_BUSY,
    AiError,
    has_reusable_meta,
    normalize_knowledge_points,
    normalize_question_type,
    normalize_subject,
)
from app.services.content_security import (
    SCENE_FORUM,
    VERDICT_RISKY,
    merge_check_text,
)
from app.utils.response import ok

logger = logging.getLogger(__name__)

# 入参上限（与前端 constants 对齐）
CONTENT_MAX_LENGTH = 2000
ANSWER_MAX_LENGTH = 4000
SUBJECT_MAX_LENGTH = 16
KNOWLEDGE_POINT_MAX_LENGTH = 32
KNOWLEDGE_POINTS_MAX_COUNT = 3
VALID_SUBJECTS = ("math", "physics", "chemistry", "other")

# 进程内限流：每用户 60 秒 3 次（多 worker 不共享，单实例部署下有效）
RATE_WINDOW_SECONDS = 60
RATE_MAX_CALLS = 3


def _parse_meta(payload: Dict[str, Any]) -> Dict[str, Any]:
    """解析可选分类元信息：非法值按「未携带」丢弃，不影响生成主流程。"""
    raw_subject = payload.get("subject")
    subject = ""
    if isinstance(raw_subject, str):
        candidate = raw_subject.strip().lower()
        if candidate in VALID_SUBJECTS and len(candidate) <= SUBJECT_MAX_LENGTH:
            subject = candidate

    raw_type = payload.get("questionType")
    question_type = ""
    if isinstance(raw_type, str):
        candidate = raw_type.strip()
        if candidate and len(candidate) <= SUBJECT_MAX_LENGTH:
            question_type = candidate

    raw_points = payload.get("knowledgePoints")
    points: List[str] = []
    if isinstance(raw_points, list):
        valid = True
        collected: List[str] = []
        for item in raw_points:
            if not isinstance(item, str):
                valid = False
                break
            label = item.strip()
            if not label or len(label) > KNOWLEDGE_POINT_MAX_LENGTH:
                valid = False
                break
            if label not in collected:
                collected.append(label)
        if valid:
            points = collected[:KNOWLEDGE_POINTS_MAX_COUNT]

    return {
        "subject": subject,
        "questionType": question_type,
        "knowledgePoints": points,
    }


def _parse_payload(payload: Any) -> Dict[str, Any]:
    """校验入参，非法时抛 2005。"""
    if not isinstance(payload, dict):
        raise ApiError(CODE_PARAM_INVALID, "参数有误，请检查后重试")

    content = payload.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ApiError(CODE_PARAM_INVALID, "题目内容不能为空")
    content = content.strip()
    if len(content) > CONTENT_MAX_LENGTH:
        raise ApiError(CODE_PARAM_INVALID, "题目内容过长，请精简后重试")

    answer = payload.get("answer", "")
    if answer is None:
        answer = ""
    if not isinstance(answer, str):
        raise ApiError(CODE_PARAM_INVALID, "答案格式有误")
    answer = answer.strip()
    if len(answer) > ANSWER_MAX_LENGTH:
        raise ApiError(CODE_PARAM_INVALID, "答案过长，请精简后重试")

    question_id = payload.get("questionId") or ""
    if not isinstance(question_id, str):
        question_id = ""
    fields: Dict[str, Any] = {
        "content": content,
        "answer": answer,
        "questionId": question_id,
    }
    fields.update(_parse_meta(payload))
    return fields


def _load_stored_points(raw: Any) -> List[str]:
    """解析库内知识点 JSON 字符串；异常降级为空数组。"""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return []
    if not isinstance(parsed, list):
        return []
    return normalize_knowledge_points(parsed)


def _load_stored_meta(
    db: Any, user_id: Any, question_id: str
) -> Dict[str, Any]:
    """按 questionId 读取云端元信息；缺失 / 已删除 / 查询异常均返回空字典。"""
    if db is None or not user_id or not question_id:
        return {}
    try:
        row = (
            db.query(QuestionSync)
            .filter(
                QuestionSync.user_id == user_id,
                QuestionSync.item_id == question_id,
            )
            .one_or_none()
        )
    except Exception:  # noqa: BLE001 - 查库失败降级，不阻断生成
        logger.warning("ai variants load stored meta failed", exc_info=True)
        return {}
    if row is None or row.deleted:
        return {}
    return {
        "subject": normalize_subject(row.subject),
        "questionType": normalize_question_type(row.question_type),
        "knowledgePoints": _load_stored_points(row.knowledge_points),
    }


def _resolve_meta(db: Any, user: Any, fields: Dict[str, Any]) -> Dict[str, Any]:
    """库内元信息优先，客户端入参按字段兜底（覆盖尚未同步的窗口期）。"""
    user_id = getattr(user, "id", None) if user is not None else None
    stored = _load_stored_meta(db, user_id, fields["questionId"])
    subject = stored.get("subject") or fields["subject"]
    question_type = stored.get("questionType") or fields["questionType"]
    points = stored.get("knowledgePoints") or fields["knowledgePoints"]

    if stored:
        meta_source = "db"
    elif subject or question_type or points:
        meta_source = "payload"
    else:
        meta_source = "none"

    return {
        "subject": subject,
        "question_type": question_type,
        "knowledge_points": points,
        "meta_source": meta_source,
    }


def create_ai_router(
    generator: Any,
    content_security: Any = None,
    auth_dep: Optional[Callable[..., Any]] = None,
    db_dep: Optional[Callable[..., Any]] = None,
) -> APIRouter:
    """构造 AI 路由。

    generator 需实现 generate(stem, answer, count) -> VariantResult；
    auth_dep 传入时该接口需登录后调用（AUTH_REQUIRED=true 时由 main 注入）；
    db_dep 传入时按 questionId 查询库内元信息（匿名或未注入时跳过）。
    """
    router = APIRouter()

    def _anonymous() -> None:
        return None

    def _no_db() -> Any:
        yield None

    user_dependency = auth_dep if auth_dep is not None else _anonymous
    database_dependency = db_dep if db_dep is not None else _no_db

    # 限流窗口：key -> 最近命中时间戳（单调时钟）
    hits: Dict[str, List[float]] = {}
    lock = threading.Lock()

    def _allow(key: str) -> bool:
        now = time.monotonic()
        with lock:
            recent = [item for item in hits.get(key, []) if now - item < RATE_WINDOW_SECONDS]
            if len(recent) >= RATE_MAX_CALLS:
                hits[key] = recent
                return False
            recent.append(now)
            hits[key] = recent
            return True

    @router.post("/ai/variants")
    async def generate_variants(
        payload: Dict[str, Any],
        request: Request,
        user: Any = Depends(user_dependency),
        db: Any = Depends(database_dependency),
    ) -> dict:
        fields = _parse_payload(payload)

        if user is not None:
            rate_key = f"user:{getattr(user, 'id', 0)}"
        else:
            remote = request.client.host if request.client else "unknown"
            rate_key = f"ip:{remote}"
        if not _allow(rate_key):
            raise ApiError(CODE_AI_RATE_LIMITED, "操作太频繁，请稍后再试")

        settings = get_current_settings()
        trace_id = uuid.uuid4().hex[:12]
        meta = _resolve_meta(db, user, fields)
        reused_meta = has_reusable_meta(
            meta["subject"], meta["knowledge_points"]
        )
        try:
            if reused_meta:
                # 元信息已知时只生成变式，跳过重新分类（库内值优先）
                result = generator.generate(
                    fields["content"],
                    fields["answer"],
                    settings.ai_max_variants,
                    subject=meta["subject"],
                    question_type=meta["question_type"],
                    knowledge_points=meta["knowledge_points"],
                )
            else:
                result = generator.generate(
                    fields["content"], fields["answer"], settings.ai_max_variants
                )
        except AiError as exc:
            raise ApiError(exc.code, exc.message) from exc
        except Exception as exc:  # noqa: BLE001 - 兜底为可重试错误
            logger.exception("ai variants unexpected failure trace=%s", trace_id)
            raise ApiError(CODE_AI_UPSTREAM_BUSY, "AI 太忙了，请稍后再试") from exc

        # 生成结果合并送检一次；服务未就绪 / 异常时由 ContentSecurityService 降级放行
        if content_security is not None and getattr(content_security, "ready", False):
            merged = "\n".join(
                merge_check_text(item.get("stem", ""), item.get("answer", ""))
                for item in result.variants
            )
            openid = getattr(user, "openid", "") if user is not None else ""
            if content_security.check_text(merged, openid, SCENE_FORUM) == VERDICT_RISKY:
                logger.warning(
                    "ai variants content risky trace=%s question=%s",
                    trace_id,
                    fields["questionId"],
                )
                raise ApiError(CODE_AI_CONTENT_RISKY, "生成内容不合规，请换一道题试试")

        logger.info(
            "ai variants ok trace=%s question=%s count=%s reused_meta=%s meta_source=%s",
            trace_id,
            fields["questionId"],
            len(result.variants),
            reused_meta,
            meta["meta_source"],
        )
        return ok(
            {
                "subject": result.subject,
                "questionType": result.question_type,
                "knowledgePoints": result.knowledge_points,
                "variants": result.variants,
                "traceId": trace_id,
            }
        )

    return router
