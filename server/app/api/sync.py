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
from app.services.content_security import (
    SCENE_FORUM,
    VERDICT_RISKY,
    ContentSecurityService,
    merge_check_text,
)
from app.utils.response import ok

_REQUIRED_KEYS = ("id", "content", "answer", "createdAt", "updatedAt", "deleted")
# 复习排期为可选字段：旧客户端不带，服务端保留库内值
_OPTIONAL_INT_KEYS = ("reviewStage", "nextReviewAt", "lastReviewedAt")
# 内容哈希为可选字段：旧客户端不带，服务端保留库内值
_OPTIONAL_STR_KEYS = ("contentHash",)


def _is_int(value: Any) -> bool:
    """排除 bool（Python 中 bool 是 int 子类）。"""
    return isinstance(value, int) and not isinstance(value, bool)


def _has_schedule(raw: Dict[str, Any]) -> bool:
    return any(key in raw for key in _OPTIONAL_INT_KEYS)


def _apply_schedule(row: QuestionSync, raw: Dict[str, Any]) -> None:
    """仅在请求显式携带排期字段时覆盖，避免旧客户端清空排期。"""
    if "reviewStage" in raw:
        row.review_stage = raw["reviewStage"]
    if "nextReviewAt" in raw:
        row.next_review_at = raw["nextReviewAt"]
    if "lastReviewedAt" in raw:
        row.last_reviewed_at = raw["lastReviewedAt"]


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
    if not _is_int(raw["createdAt"]) or not _is_int(raw["updatedAt"]):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    if not isinstance(raw["deleted"], bool):
        raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    for key in _OPTIONAL_INT_KEYS:
        if key in raw and raw[key] is not None and not _is_int(raw[key]):
            raise ApiError(CODE_SYNC_PAYLOAD_INVALID, "同步数据格式错误")
    for key in _OPTIONAL_STR_KEYS:
        if key in raw and raw[key] is not None and not isinstance(raw[key], str):
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
        "contentHash": row.content_hash,
        "reviewStage": row.review_stage,
        "nextReviewAt": row.next_review_at,
        "lastReviewedAt": row.last_reviewed_at,
    }


def _apply_content_hash(row: QuestionSync, raw: Dict[str, Any]) -> None:
    """仅在请求显式携带 contentHash 时覆盖。"""
    if "contentHash" in raw:
        row.content_hash = raw["contentHash"] or None


def create_sync_router(content_security: ContentSecurityService) -> APIRouter:
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
        rejected: List[str] = []

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
            # 仅对新增/内容实际变化的项做内容安全兜底（排期变化不重复送检）
            newer = row is None or item["updatedAt"] > row.updated_at
            content_changed = (
                row is None
                or item["content"] != row.content
                or item["answer"] != row.answer
            )
            if newer and content_changed and not item["deleted"]:
                text = merge_check_text(item["content"], item["answer"])
                if text and content_security.check_text(
                    text, user.openid, SCENE_FORUM
                ) == VERDICT_RISKY:
                    rejected.append(item["id"])
                    continue  # 不落库、不计入 accepted

            if row is None:
                row = QuestionSync(
                    user_id=user.id,
                    item_id=item["id"],
                    content=item["content"],
                    answer=item["answer"],
                    created_at=item["createdAt"],
                    updated_at=item["updatedAt"],
                    deleted=item["deleted"],
                    synced_at=server_time,
                )
                _apply_schedule(row, item)
                _apply_content_hash(row, item)
                db.add(row)
            else:
                if newer:
                    # 新者优先：仅当上行更新时才覆盖内容
                    row.content = item["content"]
                    row.answer = item["answer"]
                    row.created_at = item["createdAt"]
                    row.updated_at = item["updatedAt"]
                    row.deleted = item["deleted"]
                # 排期字段独立合并：显式携带即覆盖，缺失则保留库内值
                if _has_schedule(item):
                    _apply_schedule(row, item)
                _apply_content_hash(row, item)
                if newer or _has_schedule(item) or "contentHash" in item:
                    row.synced_at = server_time
            accepted.append(item["id"])

        db.commit()
        return ok({"accepted": accepted, "rejected": rejected, "serverTime": server_time})

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
