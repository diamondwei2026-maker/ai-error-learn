"""接口数据模型（字段名与前端约定保持一致）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class OcrResponse(BaseModel):
    """OCR 接口响应（对齐方案设计文档 §7.1）。"""

    code: int
    text: str = ""
    wordsCount: int = 0
    message: Optional[str] = None


class AiResponse(BaseModel):
    """AI 预留接口响应。"""

    code: int
    message: str
