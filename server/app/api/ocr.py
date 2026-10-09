"""OCR 接口：接收 multipart 图片，返回清洗后的纯文本题干。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, UploadFile

from app.models.schemas import OcrResponse
from app.services.aliyun_ocr import CODE_IMAGE_TOO_LARGE, OcrError


def create_ocr_router(service: Any, max_image_bytes: int) -> APIRouter:
    """构造 OCR 路由。service 需实现 recognize(bytes) -> OcrOutcome。"""
    router = APIRouter()

    @router.post("/ocr", response_model=OcrResponse, response_model_exclude_none=True)
    async def recognize(file: UploadFile = File(...)) -> OcrResponse:
        data = await file.read()
        if not data:
            return OcrResponse(code=CODE_IMAGE_TOO_LARGE, message="图片为空，请重新拍摄或选择")
        if len(data) > max_image_bytes:
            return OcrResponse(code=CODE_IMAGE_TOO_LARGE, message="图片过大，请重新拍摄")
        content_type = file.content_type or ""
        if content_type and not content_type.startswith("image/"):
            return OcrResponse(code=CODE_IMAGE_TOO_LARGE, message="文件不是图片，请重新选择")

        try:
            outcome = service.recognize(data)
        except OcrError as exc:
            return OcrResponse(code=exc.code, message=exc.message)

        return OcrResponse(code=0, text=outcome.text, wordsCount=outcome.words_count)

    return router
