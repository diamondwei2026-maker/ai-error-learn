"""AI 接口（预留）：本期固定返回 501 / code 9001。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def create_ai_router() -> APIRouter:
    router = APIRouter()

    @router.post("/ai/variants")
    async def generate_variants() -> JSONResponse:
        # LangChain 接入点在 app/services/ai_service.py，启用后在此调用 VariantGenerator
        return JSONResponse(
            status_code=501,
            content={"code": 9001, "message": "AI 功能未启用"},
        )

    return router
