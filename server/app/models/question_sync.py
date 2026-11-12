"""错题同步表模型（仅文本，不含原图）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuestionSync(Base):
    """用户错题的云端副本，以 (user_id, item_id) 唯一。"""

    __tablename__ = "question_sync"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id", name="uq_question_sync_user_item"),
        Index("ix_question_sync_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    item_id: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 复习排期（可空：旧客户端上行不带这些字段时保留库内值）
    review_stage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    next_review_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_reviewed_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
