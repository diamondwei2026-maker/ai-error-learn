"""复习提醒接口：客户端读取推送配置、上报订阅授权结果。"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.deps.auth import get_current_user
from app.errors import (
    CODE_REMINDER_NOT_READY,
    CODE_REMINDER_PARAM_INVALID,
    ApiError,
)
from app.models.reminder_subscription import ReminderSubscription
from app.models.user import User
from app.services import auth_service
from app.utils.response import ok


def _is_int(value: Any) -> bool:
    """排除 bool（Python 中 bool 是 int 子类）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def create_reminder_router(settings: Settings) -> APIRouter:
    """构造提醒路由。"""
    router = APIRouter()

    @router.get("/reminder/config")
    async def config() -> dict:
        """推送配置：无鉴权可读；未配置时 enabled=false，客户端降级为站内提醒。"""
        ready = settings.reminder_ready
        return ok(
            {
                "enabled": ready,
                "templateId": settings.reminder_template_id if ready else "",
                "page": settings.reminder_page,
                "quietStart": settings.reminder_quiet_start,
                "quietEnd": settings.reminder_quiet_end,
            }
        )

    @router.post("/reminder/subscription")
    async def report_subscription(
        payload: Dict[str, Any],
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        """上报授权结果：accepted 为本次新增可发送次数，enabled=false 时清空额度。"""
        if not settings.reminder_ready:
            raise ApiError(CODE_REMINDER_NOT_READY, "提醒功能未开启")

        accepted = payload.get("accepted", 0)
        enabled = payload.get("enabled", False)
        if not _is_int(accepted) or accepted < 0 or not isinstance(enabled, bool):
            raise ApiError(CODE_REMINDER_PARAM_INVALID, "提醒参数不合法")

        row = (
            db.query(ReminderSubscription)
            .filter(ReminderSubscription.user_id == user.id)
            .one_or_none()
        )
        now = auth_service.now_ms()
        if row is None:
            row = ReminderSubscription(
                user_id=user.id, enabled=False, quota=0, updated_at=now
            )
            db.add(row)

        if enabled:
            row.enabled = True
            row.quota = min(int(row.quota or 0) + accepted, settings.reminder_max_quota)
        else:
            row.enabled = False
            row.quota = 0
        row.updated_at = now

        db.commit()
        db.refresh(row)
        return ok({"enabled": bool(row.enabled), "quota": int(row.quota or 0)})

    return router
