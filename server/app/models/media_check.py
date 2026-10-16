"""图片内容安全送检记录（微信 mediaCheckAsync 异步结果匹配）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

VERDICT_PENDING = "pending"
VERDICT_PASS = "pass"
VERDICT_RISKY = "risky"
VERDICT_REVIEW = "review"
VERDICT_ERROR = "error"


class MediaCheckRecord(Base):
    """一次图片异步送检。trace_id 为微信回调的匹配键。"""

    __tablename__ = "media_check_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    # 落盘文件名（如 "1.png"），命中违规后据此定位并删除
    file_name: Mapped[str] = mapped_column(String(128), nullable=False)
    media_url: Mapped[str] = mapped_column(String(255), nullable=False)
    verdict: Mapped[str] = mapped_column(String(16), nullable=False, default=VERDICT_PENDING)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checked_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
