"""复习提醒调度单测：窗口 / 静默 / 降频 / 额度 / 每日幂等。"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.config import Settings
from app.db.session import get_session_factory
from app.models.question_sync import QuestionSync
from app.models.reminder_subscription import ReminderSubscription
from app.models.user import User
from app.services.reminder_scheduler import (
    ReminderScheduler,
    in_quiet_hours,
    in_reminder_window,
    is_downgraded,
    should_send,
)
from app.services.wechat_service import SendMessageResult

TZ = ZoneInfo("Asia/Shanghai")
WEDNESDAY = datetime(2026, 11, 11, 20, 1, tzinfo=TZ)
MONDAY = datetime(2026, 11, 9, 20, 1, tzinfo=TZ)


class FakeWechat:
    """替身：记录发送调用，可切换失败。"""

    def __init__(self) -> None:
        self.calls = []
        self.fail = False

    def send_subscribe_message(self, openid, template_id, data, page=""):
        self.calls.append(
            {"openid": openid, "templateId": template_id, "data": data, "page": page}
        )
        if self.fail:
            return SendMessageResult(False, "43101: user refuse")
        return SendMessageResult(True)


@pytest.fixture()
def fake_wechat() -> FakeWechat:
    return FakeWechat()


@pytest.fixture()
def ready_settings(settings: Settings) -> Settings:
    return replace(settings, reminder_enabled=True, reminder_template_id="tpl-reminder")


@pytest.fixture()
def scheduler(ready_settings: Settings, client, fake_wechat: FakeWechat) -> ReminderScheduler:
    """client 夹具负责建库；调度器复用同一引擎。"""
    return ReminderScheduler(ready_settings, fake_wechat)


def seed_user(
    now: datetime,
    *,
    due_count: int = 2,
    quota: int = 2,
    enabled: bool = True,
    last_sent_at: Optional[int] = None,
    last_reviewed_at: Optional[int] = None,
) -> int:
    timestamp = int(now.timestamp() * 1000)
    session = get_session_factory()()
    try:
        user = User(
            openid=f"openid-{uuid4().hex[:8]}",
            created_at=timestamp - 30 * 24 * 3600 * 1000,
            updated_at=timestamp,
            last_login_at=timestamp,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        for index in range(due_count):
            session.add(
                QuestionSync(
                    user_id=user.id,
                    item_id=f"q{index}",
                    content="题干",
                    answer="答案",
                    created_at=timestamp - 1000,
                    updated_at=timestamp - 1000,
                    deleted=False,
                    synced_at=timestamp - 1000,
                    review_stage=1,
                    next_review_at=timestamp - 1000,
                    last_reviewed_at=last_reviewed_at,
                )
            )
        session.add(
            ReminderSubscription(
                user_id=user.id,
                enabled=enabled,
                quota=quota,
                last_sent_at=last_sent_at,
                updated_at=timestamp,
            )
        )
        session.commit()
        return user.id
    finally:
        session.close()


def get_subscription(user_id: int) -> ReminderSubscription:
    session = get_session_factory()()
    try:
        return (
            session.query(ReminderSubscription)
            .filter(ReminderSubscription.user_id == user_id)
            .one()
        )
    finally:
        session.close()


# ---------- 纯函数 ----------


def test_in_reminder_window() -> None:
    assert in_reminder_window(WEDNESDAY.replace(minute=0), 20) is True
    assert in_reminder_window(WEDNESDAY.replace(minute=4), 20) is True
    assert in_reminder_window(WEDNESDAY.replace(minute=5), 20) is False
    assert in_reminder_window(WEDNESDAY.replace(hour=19), 20) is False


def test_in_quiet_hours_cross_midnight() -> None:
    assert in_quiet_hours(WEDNESDAY.replace(hour=21, minute=0), 21, 8) is True
    assert in_quiet_hours(WEDNESDAY.replace(hour=7, minute=59), 21, 8) is True
    assert in_quiet_hours(WEDNESDAY.replace(hour=20), 21, 8) is False
    assert in_quiet_hours(WEDNESDAY.replace(hour=8, minute=0), 21, 8) is False


def test_is_downgraded() -> None:
    recent = int((WEDNESDAY - timedelta(days=2)).timestamp() * 1000)
    stale = int((WEDNESDAY - timedelta(days=4)).timestamp() * 1000)
    assert is_downgraded(WEDNESDAY, recent, None) is False
    assert is_downgraded(WEDNESDAY, stale, None) is True
    # 从未复习过的新用户以账号创建时间起算
    assert is_downgraded(WEDNESDAY, None, stale) is True
    assert is_downgraded(WEDNESDAY, None, None) is False


def test_should_send_gates() -> None:
    recent = int((WEDNESDAY - timedelta(days=1)).timestamp() * 1000)
    stale = int((WEDNESDAY - timedelta(days=4)).timestamp() * 1000)
    base = {
        "enabled": True,
        "quota": 1,
        "last_sent_at": None,
        "last_reviewed_at": recent,
        "created_at": None,
        "quiet_start": 21,
        "quiet_end": 8,
    }
    assert should_send(WEDNESDAY, **base) is True
    assert should_send(WEDNESDAY, **{**base, "enabled": False}) is False
    assert should_send(WEDNESDAY, **{**base, "quota": 0}) is False
    assert should_send(
        WEDNESDAY,
        **{**base, "last_sent_at": int(WEDNESDAY.timestamp() * 1000)},
    ) is False
    assert should_send(WEDNESDAY.replace(hour=22), **base) is False
    # 连续 3 天未复习：周三不发送，周一发送
    assert should_send(WEDNESDAY, **{**base, "last_reviewed_at": stale}) is False
    assert should_send(MONDAY, **{**base, "last_reviewed_at": stale}) is True


# ---------- 调度 tick ----------


def test_tick_sends_once_and_decrements_quota(scheduler, fake_wechat) -> None:
    recent = int((WEDNESDAY - timedelta(days=1)).timestamp() * 1000)
    user_id = seed_user(WEDNESDAY, due_count=3, quota=2, last_reviewed_at=recent)

    first = scheduler.run_tick(WEDNESDAY)
    assert first == {"dueUsers": 1, "sent": 1, "skipped": 0, "failed": 0}
    assert len(fake_wechat.calls) == 1
    assert fake_wechat.calls[0]["page"] == "pages/quiz/index"
    data = fake_wechat.calls[0]["data"]
    assert data["thing1"]["value"] == "错题复习提醒"
    assert data["number16"]["value"] == 3
    assert data["time23"]["value"] == "20:01"
    assert data["thing12"]["value"] == "点击进入按到期顺序复习"

    second = scheduler.run_tick(WEDNESDAY)
    assert second["sent"] == 0
    assert len(fake_wechat.calls) == 1
    assert get_subscription(user_id).quota == 1


def test_tick_outside_window_does_nothing(scheduler, fake_wechat) -> None:
    seed_user(WEDNESDAY, last_reviewed_at=int(WEDNESDAY.timestamp() * 1000))
    stats = scheduler.run_tick(WEDNESDAY.replace(hour=19, minute=30))
    assert stats == {"dueUsers": 0, "sent": 0, "skipped": 0, "failed": 0}
    assert fake_wechat.calls == []


@pytest.mark.parametrize("enabled,quota", [(False, 2), (True, 0)])
def test_tick_skips_disabled_or_no_quota(scheduler, fake_wechat, enabled, quota) -> None:
    seed_user(
        WEDNESDAY,
        enabled=enabled,
        quota=quota,
        last_reviewed_at=int((WEDNESDAY - timedelta(days=1)).timestamp() * 1000),
    )
    stats = scheduler.run_tick(WEDNESDAY)
    assert stats["sent"] == 0
    assert stats["skipped"] == 1
    assert fake_wechat.calls == []


def test_tick_skips_quiet_hours(
    ready_settings: Settings, client, fake_wechat: FakeWechat
) -> None:
    quiet_scheduler = ReminderScheduler(replace(ready_settings, reminder_hour=22), fake_wechat)
    seed_user(
        WEDNESDAY,
        last_reviewed_at=int((WEDNESDAY - timedelta(days=1)).timestamp() * 1000),
    )
    stats = quiet_scheduler.run_tick(WEDNESDAY.replace(hour=22, minute=1))
    assert stats["sent"] == 0
    assert fake_wechat.calls == []


def test_tick_failure_does_not_retry_same_day(scheduler, fake_wechat) -> None:
    fake_wechat.fail = True
    user_id = seed_user(
        WEDNESDAY,
        quota=2,
        last_reviewed_at=int((WEDNESDAY - timedelta(days=1)).timestamp() * 1000),
    )

    first = scheduler.run_tick(WEDNESDAY)
    assert first["failed"] == 1
    second = scheduler.run_tick(WEDNESDAY)
    assert second["sent"] == 0
    assert len(fake_wechat.calls) == 1
    # 发送失败不扣额度
    assert get_subscription(user_id).quota == 2


def test_tick_downgrades_to_monday(ready_settings: Settings, client, fake_wechat) -> None:
    downgrade_scheduler = ReminderScheduler(ready_settings, fake_wechat)
    stale = int((WEDNESDAY - timedelta(days=4)).timestamp() * 1000)
    seed_user(WEDNESDAY, last_reviewed_at=stale)

    assert downgrade_scheduler.run_tick(WEDNESDAY)["sent"] == 0
    assert fake_wechat.calls == []

    # 周一重新发送：需要当日仍有到期题
    seed_user(MONDAY, last_reviewed_at=stale)
    assert downgrade_scheduler.run_tick(MONDAY)["sent"] == 1
