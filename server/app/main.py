"""FastAPI 应用装配入口。

启动：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import create_ai_router
from app.api.ocr import create_ocr_router
from app.config import Settings, load_settings
from app.services.aliyun_ocr import AliyunOcrClient, OcrService


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()

    app = FastAPI(
        title="错题本 OCR 代理",
        version="0.1.0",
        description="仅做 OCR 密钥代理；错题数据 100% 存于小程序本地。",
    )
    # 开发期放开跨域，便于 H5 预览与真机调试
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    ocr_client = AliyunOcrClient(
        settings.access_key_id,
        settings.access_key_secret,
        settings.ocr_endpoint,
    )
    ocr_service = OcrService(ocr_client)

    app.include_router(
        create_ocr_router(ocr_service, settings.max_image_bytes),
        prefix="/api/v1",
        tags=["ocr"],
    )
    app.include_router(create_ai_router(), prefix="/api/v1", tags=["ai"])

    @app.get("/api/v1/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
