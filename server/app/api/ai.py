"""AI 举一反三接口：根据错题生成同构变式题（不入库、不排期）。"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Depends, Request

from app.config import get_current_settings
from app.errors import CODE_PARAM_INVALID, ApiError
from app.services.ai_service import (
    CODE_AI_CONTENT_RISKY,
    CODE_AI_RATE_LIMITED,
    CODE_AI_UPSTREAM_BUSY,
    AiError,
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

# 进程内限流：每用户 60 秒 3 次（多 worker 不共享，单实例部署下有效）
RATE_WINDOW_SECONDS = 60
RATE_MAX_CALLS = 3


def _parse_payload(payload: Any) -> Dict[str, str]:
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
    return {"content": content, "answer": answer, "questionId": question_id}


def create_ai_router(
    generator: Any,
    content_security: Any = None,
    auth_dep: Optional[Callable[..., Any]] = None,
) -> APIRouter:
    """构造 AI 路由。

    generator 需实现 generate(stem, answer, count) -> VariantResult；
    auth_dep 传入时该接口需登录后调用（AUTH_REQUIRED=true 时由 main 注入）。
    """
    router = APIRouter()

    def _anonymous() -> None:
        return None

    user_dependency = auth_dep if auth_dep is not None else _anonymous

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
        try:
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
            "ai variants ok trace=%s question=%s count=%s",
            trace_id,
            fields["questionId"],
            len(result.variants),
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
