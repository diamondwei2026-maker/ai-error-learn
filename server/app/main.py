"""FastAPI 应用装配入口。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.ai import create_ai_router
from app.api.auth import create_auth_router
from app.api.recognize import create_recognize_router
from app.api.sync import create_sync_router
from app.api.user import create_user_router
from app.config import Settings, load_settings, set_current_settings
from app.db import configure_database, init_db
from app.deps.auth import get_current_user
from app.errors import ApiError
from app.services.vision_recognize import VisionClient, VisionRecognizeService
from app.services.wechat_service import WechatService


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    set_current_settings(settings)
    configure_database(settings.database_url)
    init_db()

    # 启动告警：密钥缺失不阻塞启动，但需显式提示（登录功能将不可用）
    if not settings.jwt_secret:
        logging.getLogger(__name__).warning("JWT_SECRET 未配置，登录/同步接口将不可用")
    if not settings.wechat_app_secret:
        logging.getLogger(__name__).warning("WECHAT_APP_SECRET 未配置，微信登录将返回 2003")

    app = FastAPI(
        title="错题本识别代理",
        version="0.2.0",
        description="多模态识别密钥代理 + 用户账号（微信登录 / 资料 / 文本同步）。",
    )
    # 开发期放开跨域，便于 H5 预览与真机调试；生产通过 CORS_ORIGINS 收敛为白名单
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def _api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message},
        )

    vision_client = VisionClient(
        settings.vision_api_key,
        settings.vision_base_url,
        settings.vision_model,
        settings.vision_enabled,
        settings.vision_timeout,
    )
    vision_service = VisionRecognizeService(vision_client)
    wechat_service = WechatService(settings.wechat_appid, settings.wechat_app_secret)

    app.include_router(
        create_recognize_router(
            vision_service,
            settings.max_image_bytes,
            auth_dep=get_current_user if settings.auth_required else None,
        ),
        prefix="/api/v1",
        tags=["recognize"],
    )
    app.include_router(create_ai_router(), prefix="/api/v1", tags=["ai"])
    app.include_router(
        create_auth_router(wechat_service, settings), prefix="/api/v1", tags=["auth"]
    )
    app.include_router(create_user_router(settings), prefix="/api/v1", tags=["user"])
    app.include_router(create_sync_router(), prefix="/api/v1", tags=["sync"])

    # 静态资源（头像）：目录不存在时先创建，避免 StaticFiles 挂载失败
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(settings.uploads_dir)), name="static")

    @app.get("/api/v1/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
