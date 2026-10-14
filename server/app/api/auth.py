"""登录接口：微信 code 换 openid → 自建用户 → 签发 JWT。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import Settings
from app.db import get_db
from app.errors import (
    CODE_LOGIN_NOT_CONFIGURED,
    CODE_TOKEN_INVALID,
    ApiError,
    TokenError,
    WechatLoginError,
)
from app.models.schemas import LoginRequest, RefreshRequest
from app.models.user import User
from app.services import auth_service
from app.services.wechat_service import WechatService
from app.utils.response import ok


def create_auth_router(wechat_service: WechatService, settings: Settings) -> APIRouter:
    """构造登录路由。"""
    router = APIRouter()

    def _ensure_configured() -> None:
        if not settings.jwt_secret:
            raise ApiError(CODE_LOGIN_NOT_CONFIGURED, "服务端未配置登录密钥，请稍后再试")

    @router.post("/auth/login")
    async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
        _ensure_configured()
        try:
            session_info = wechat_service.code2session(payload.code)
        except WechatLoginError as exc:
            raise ApiError(exc.code, exc.message) from exc

        user = auth_service.find_or_create_user(
            db, session_info["openid"], session_info.get("unionid")
        )
        return ok(auth_service.build_session_payload(user, settings))

    @router.post("/auth/refresh")
    async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
        _ensure_configured()
        try:
            user_id = auth_service.decode_token(
                payload.refreshToken, settings, expected_type="refresh"
            )
        except TokenError as exc:
            raise ApiError(CODE_TOKEN_INVALID, exc.message, http_status=401) from exc

        user = db.get(User, user_id)
        if user is None:
            raise ApiError(CODE_TOKEN_INVALID, "登录态失效", http_status=401)
        return ok(auth_service.build_session_payload(user, settings))

    return router
