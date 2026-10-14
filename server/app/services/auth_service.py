"""JWT 签发/校验与用户装配。"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import jwt
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import TokenError
from app.models.user import User


def now_ms() -> int:
    """当前毫秒时间戳。"""
    return int(time.time() * 1000)


def _encode_token(user_id: int, settings: Settings, token_type: str, ttl: int) -> Tuple[str, int]:
    issued_at = int(time.time())
    expire_at = issued_at + int(ttl)
    payload = {"sub": str(user_id), "typ": token_type, "iat": issued_at, "exp": expire_at}
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expire_at * 1000


def create_access_token(user_id: int, settings: Settings) -> Tuple[str, int]:
    """签发 access token，返回 (token, 过期毫秒时间戳)。"""
    return _encode_token(user_id, settings, "access", settings.jwt_access_ttl)


def create_refresh_token(user_id: int, settings: Settings) -> Tuple[str, int]:
    """签发 refresh token，返回 (token, 过期毫秒时间戳)。"""
    return _encode_token(user_id, settings, "refresh", settings.jwt_refresh_ttl)


def decode_token(token: str, settings: Settings, expected_type: str = "access") -> int:
    """校验并解析 token，返回 user_id；失败抛 TokenError。"""
    if not settings.jwt_secret:
        raise TokenError("服务端未配置登录密钥")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:  # 过期 / 签名不符 / 格式错误
        raise TokenError("登录态失效") from exc

    if payload.get("typ") != expected_type:
        raise TokenError("登录态失效")

    subject = payload.get("sub")
    if not subject:
        raise TokenError("登录态失效")
    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise TokenError("登录态失效") from exc


def serialize_user(user: User) -> Dict[str, Any]:
    """用户对外表示。"""
    return {
        "id": user.id,
        "openid": user.openid,
        "nickname": user.nickname,
        "avatarUrl": user.avatar_url,
    }


def find_or_create_user(db: Session, openid: str, unionid: Optional[str] = None) -> User:
    """按 openid 查找用户，不存在则创建；每次登录刷新 last_login_at。"""
    timestamp = now_ms()
    user = db.query(User).filter(User.openid == openid).one_or_none()
    if user is None:
        user = User(
            openid=openid,
            unionid=unionid,
            created_at=timestamp,
            updated_at=timestamp,
            last_login_at=timestamp,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    if unionid and not user.unionid:
        user.unionid = unionid
    user.last_login_at = timestamp
    db.commit()
    db.refresh(user)
    return user


def build_session_payload(user: User, settings: Settings) -> Dict[str, Any]:
    """构造登录/续期响应体。"""
    access_token, access_expire_at = create_access_token(user.id, settings)
    refresh_token, _ = create_refresh_token(user.id, settings)
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "accessExpireAt": access_expire_at,
        "user": serialize_user(user),
    }
