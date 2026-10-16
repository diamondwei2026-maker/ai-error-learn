"""内容安全接口：错题内容保存前预检（服务端 sync/push 兜底同口径）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import get_current_user
from app.errors import CODE_SYNC_CONTENT_RISK, ApiError
from app.models.schemas import TextCheckRequest
from app.models.user import User
from app.services.content_security import (
    SCENE_FORUM,
    VERDICT_RISKY,
    ContentSecurityService,
    merge_check_text,
)
from app.utils.response import ok


def create_security_router(content_security: ContentSecurityService) -> APIRouter:
    """构造内容安全路由（需登录）。"""
    router = APIRouter()

    @router.post("/security/text-check")
    async def text_check(
        payload: TextCheckRequest,
        user: User = Depends(get_current_user),
    ) -> dict:
        text = merge_check_text(payload.content, payload.answer)
        if not text:
            return ok({"pass": True})
        if content_security.check_text(text, user.openid, SCENE_FORUM) == VERDICT_RISKY:
            raise ApiError(CODE_SYNC_CONTENT_RISK, "题干或答案包含违规内容，请修改后重试")
        return ok({"pass": True})

    return router
