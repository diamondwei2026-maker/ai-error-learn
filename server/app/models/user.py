"""用户表模型。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """微信小程序用户。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    unionid: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_login_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
