"""接口数据模型（字段名与前端约定保持一致）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RecognizeResponse(BaseModel):
    """识别接口响应（对齐方案设计文档 §7.1）。

    text 为识别出的题干；answer 为识别出的答案（可为空）；
    splitMethod ∈ {vlm, none}，vlm 表示由多模态大模型识别得到答案。
    """

    code: int
    text: str = ""
    answer: str = ""
    splitMethod: str = ""
    wordsCount: int = 0
    message: Optional[str] = None


class AiResponse(BaseModel):
    """AI 预留接口响应。"""

    code: int
    message: str


# ---------- 用户 / 登录 / 同步 ----------


class LoginRequest(BaseModel):
    """微信登录请求：code 来自 wx.login。"""

    code: str


class RefreshRequest(BaseModel):
    """登录续期请求。"""

    refreshToken: str


class UpdateProfileRequest(BaseModel):
    """更新用户资料（当前仅昵称）。"""

    nickname: Optional[str] = None


class SyncPushRequest(BaseModel):
    """同步上行：items 结构在接口内显式校验，非法返回 3001。"""

    items: List[Dict[str, Any]] = []
    cursor: Optional[int] = None
