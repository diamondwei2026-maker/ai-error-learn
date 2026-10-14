"""错题同步表模型（仅文本，不含原图）。"""

from __future__ import annotations

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
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
