"""复习提醒订阅状态（一次性订阅消息额度与发送记录）。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import BigInteger, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReminderSubscription(Base):
    """用户订阅提醒状态，以 user_id 唯一。

    quota 为剩余可发送次数（每次授权 +1，上限由配置控制）；
    last_sent_at 同时用于「每日最多 1 条」与发送幂等。
    """

    __tablename__ = "reminder_subscription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quota: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sent_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    updated_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
