"""用户资料接口：查看/更新资料、上传头像、注销账号。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.deps.auth import get_current_user
from app.errors import CODE_AVATAR_INVALID, CODE_PARAM_INVALID, ApiError
from app.models.question_sync import QuestionSync
from app.models.schemas import UpdateProfileRequest
from app.models.user import User
from app.services import auth_service
from app.utils.response import ok

NICKNAME_MAX_LENGTH = 32

_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _ext_for(content_type: str) -> str:
    return _EXT_BY_CONTENT_TYPE.get((content_type or "").lower(), ".jpg")


def _remove_avatars(avatar_dir: Path, user_id: int) -> None:
    if not avatar_dir.is_dir():
        return
    for path in avatar_dir.glob(f"{user_id}.*"):
        try:
            path.unlink()
        except OSError:
            pass


def create_user_router(settings: Settings) -> APIRouter:
    """构造用户路由。"""
    router = APIRouter()

    @router.get("/user/me")
    async def me(user: User = Depends(get_current_user)) -> dict:
        return ok({"user": auth_service.serialize_user(user)})

    @router.patch("/user/me")
    async def update_profile(
        payload: UpdateProfileRequest,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        if payload.nickname is not None:
            nickname = payload.nickname.strip()
            if len(nickname) > NICKNAME_MAX_LENGTH:
                raise ApiError(CODE_PARAM_INVALID, f"昵称不能超过 {NICKNAME_MAX_LENGTH} 个字符")
            user.nickname = nickname or None
        user.updated_at = auth_service.now_ms()
        db.commit()
        db.refresh(user)
        return ok({"user": auth_service.serialize_user(user)})

    @router.post("/user/avatar")
    async def upload_avatar(
        file: UploadFile = File(...),
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        data = await file.read()
        if not data or len(data) > settings.avatar_max_bytes:
            raise ApiError(CODE_AVATAR_INVALID, "头像文件无效或过大，请重新选择")
        content_type = file.content_type or ""
        if content_type and not content_type.startswith("image/"):
            raise ApiError(CODE_AVATAR_INVALID, "请选择图片文件")

        avatar_dir = settings.avatar_dir
        avatar_dir.mkdir(parents=True, exist_ok=True)
        _remove_avatars(avatar_dir, user.id)
        target = avatar_dir / f"{user.id}{_ext_for(content_type)}"
        target.write_bytes(data)

        user.avatar_url = f"/static/avatars/{target.name}?v={auth_service.now_ms()}"
        user.updated_at = auth_service.now_ms()
        db.commit()
        db.refresh(user)
        return ok({"user": auth_service.serialize_user(user)})

    @router.post("/user/delete")
    async def delete_account(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        user_id = user.id
        db.query(QuestionSync).filter(QuestionSync.user_id == user_id).delete()
        db.delete(user)
        db.commit()
        _remove_avatars(settings.avatar_dir, user_id)
        return ok({"deleted": True})

    return router
