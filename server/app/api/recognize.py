"""识别接口：接收 multipart 图片，由多模态大模型一步返回题干 + 答案。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, UploadFile

from app.models.schemas import RecognizeResponse
from app.services.vision_recognize import CODE_IMAGE_TOO_LARGE, RecognizeError
from app.utils.text_clean import count_words


def create_recognize_router(service: Any, max_image_bytes: int) -> APIRouter:
    """构造识别路由。service 需实现 recognize(bytes, mime_type) -> RecognizeOutcome。"""
    router = APIRouter()

    @router.post("/recognize", response_model=RecognizeResponse, response_model_exclude_none=True)
    async def recognize(file: UploadFile = File(...)) -> RecognizeResponse:
        data = await file.read()
        if not data:
            return RecognizeResponse(code=CODE_IMAGE_TOO_LARGE, message="图片为空，请重新拍摄或选择")
        if len(data) > max_image_bytes:
            return RecognizeResponse(code=CODE_IMAGE_TOO_LARGE, message="图片过大，请重新拍摄")
        content_type = file.content_type or ""
        if content_type and not content_type.startswith("image/"):
            return RecognizeResponse(code=CODE_IMAGE_TOO_LARGE, message="文件不是图片，请重新选择")

        try:
            outcome = service.recognize(data, content_type or "image/jpeg")
        except RecognizeError as exc:
            return RecognizeResponse(code=exc.code, message=exc.message)

        return RecognizeResponse(
            code=0,
            text=outcome.stem,
            answer=outcome.answer,
            splitMethod="vlm" if outcome.answer else "none",
            wordsCount=count_words(outcome.stem),
        )

    return router
