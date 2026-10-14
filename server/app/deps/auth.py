"""鉴权依赖：Bearer token → JWT 校验 → 当前用户。"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import get_current_settings
from app.db import get_db
from app.errors import (
    CODE_TOKEN_INVALID,
    CODE_UNAUTHORIZED,
    ApiError,
    TokenError,
)
from app.models.user import User
from app.services.auth_service import decode_token


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise ApiError(CODE_UNAUTHORIZED, "未登录", http_status=401)
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise ApiError(CODE_UNAUTHORIZED, "未登录", http_status=401)
    return parts[1].strip()


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """强制鉴权：无有效 token 时抛出 401。"""
    token = _extract_bearer(authorization)
    settings = get_current_settings()
    try:
        user_id = decode_token(token, settings, expected_type="access")
    except TokenError as exc:
        raise ApiError(CODE_TOKEN_INVALID, exc.message, http_status=401) from exc

    user = db.get(User, user_id)
    if user is None:
        raise ApiError(CODE_TOKEN_INVALID, "登录态失效", http_status=401)
    return user


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选鉴权：无 token 返回 None，不抛错。"""
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except ApiError:
        return None
