"""错题同步接口：上行 UPSERT（新者优先）+ 下行增量拉取。"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps.auth import get_current_user
from app.errors import CODE_SYNC_PAYLOAD_INVALID, ApiError
from app.models.question_sync import QuestionSync
from app.models.schemas import SyncPushRequest
from app.models.user import User
from app.services import auth_service
from app.utils.response import ok

_REQUIRED_KEYS = ("id", "content", "answer", "createdAt", "updatedAt", "deleted")


def _validate_item(raw: Any) -> Dict[str, Any]:
    """校验单个同步项，非法抛 3001。"""
    if not isinstance(raw, dict):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    if not isinstance(raw["id"], str) or not raw["id"].strip():
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    if not isinstance(raw["content"], str) or not isinstance(raw["answer"], str):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    if not isinstance(raw["createdAt"], int) or not isinstance(raw["updatedAt"], int):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    if not isinstance(raw["deleted"], bool):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    return raw


def _serialize(row: QuestionSync) -> Dict[str, Any]:
    return {
        "id": row.item_id,
        "content": row.content,
        "answer": row.answer,
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
        "deleted": bool(row.deleted),
    }


def create_sync_router() -> APIRouter:
    """构造同步路由。"""
    router = APIRouter()

    @router.post("/sync/push")
    async def push(
        payload: SyncPushRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        server_time = auth_service.now_ms()
        accepted: List[str] = []

        for raw in payload.items:
            item = _validate_item(raw)
            row = (
                db.query(QuestionSync)
                .filter(
                    QuestionSync.user_id == user.id,
                    QuestionSync.item_id == item["id"],
                )
                .one_or_none()
            )
            if row is None:
                db.add(
                    QuestionSync(
                        user_id=user.id,
                        item_id=item["id"],
                        content=item["content"],
                        answer=item["answer"],
                        created_at=item["createdAt"],
                        updated_at=item["updatedAt"],
                        deleted=item["deleted"],
                        synced_at=server_time,
                    )
                )
            elif item["updatedAt"] > row.updated_at:
                # 新者优先：仅当上行更新时才覆盖
                row.content = item["content"]
                row.answer = item["answer"]
                row.created_at = item["createdAt"]
                row.updated_at = item["updatedAt"]
                row.deleted = item["deleted"]
                row.synced_at = server_time
            accepted.append(item["id"])

        db.commit()
        return ok({"accepted": accepted, "serverTime": server_time})

    @router.get("/sync/pull")
    async def pull(
        since: int = 0,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        rows = (
            db.query(QuestionSync)
            .filter(QuestionSync.user_id == user.id, QuestionSync.synced_at > since)
            .order_by(QuestionSync.synced_at.asc(), QuestionSync.id.asc())
            .all()
        )
        return ok(
            {
                "items": [_serialize(row) for row in rows],
                "serverTime": auth_service.now_ms(),
            }
        )

    return router
