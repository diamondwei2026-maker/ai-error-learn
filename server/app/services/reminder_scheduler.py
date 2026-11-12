"""每日复习提醒调度器。

APScheduler 每 5 分钟 tick 一次，仅在东八区配置的发送时刻窗口内执行：
汇总当日到期错题 → 过滤开关/额度/静默/降频 → 聚合成一条订阅消息发送。

幂等：发送前用 `last_sent_at` 条件更新「抢占」，同一窗口重复 tick 或
多实例并行时只有一次更新成功，因此每个用户每日最多发送 1 条。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.session import get_session_factory
from app.models.question_sync import QuestionSync
from app.models.reminder_subscription import ReminderSubscription
from app.models.user import User
from app.services.wechat_service import SendMessageResult, WechatService

_logger = logging.getLogger(__name__)

# 调度粒度与发送窗口（分钟）
TICK_MINUTES = 5
WINDOW_MINUTES = 5
# 连续 N 天未复习后降频为每周一次
DOWNGRADE_DAYS = 3

# 订阅消息模板字段映射（模板：事项主题 / 事项数目 / 提醒时间 / 备注消息）
TEMPLATE_FIELD_TITLE = "thing1"
TEMPLATE_FIELD_COUNT = "number16"
TEMPLATE_FIELD_TIME = "time23"
TEMPLATE_FIELD_TIP = "thing12"


def resolve_timezone(name: str) -> ZoneInfo:
    """解析时区；非法配置回退 Asia/Shanghai，避免调度器启动失败。"""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        _logger.warning("REMINDER_TIMEZONE=%s 不可用，回退 Asia/Shanghai", name)
        return ZoneInfo("Asia/Shanghai")


def day_start_ms(now: datetime) -> int:
    """本地当日 00:00 的毫秒时间戳。"""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


def day_end_ms(now: datetime) -> int:
    """次日 00:00 的毫秒时间戳（作为「今天到期」的闭区间上界）。"""
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return int(start.timestamp() * 1000)


def in_reminder_window(now: datetime, hour: int) -> bool:
    """是否落在发送时刻的窗口内（如 20:00–20:05）。"""
    return now.hour == hour and now.minute < WINDOW_MINUTES


def in_quiet_hours(now: datetime, quiet_start: int, quiet_end: int) -> bool:
    """是否处于静默时段，支持跨午夜（如 21:00–08:00）。"""
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= now.hour < quiet_end
    return now.hour >= quiet_start or now.hour < quiet_end


def is_downgraded(
    now: datetime,
    last_reviewed_at: Optional[int],
    created_at: Optional[int],
) -> bool:
    """连续 3 天无复习 → 降频。从未复习过的新用户以账号创建时间起算。"""
    reference = last_reviewed_at or created_at
    if reference is None:
        return False
    elapsed_ms = now.timestamp() * 1000 - reference
    return elapsed_ms >= DOWNGRADE_DAYS * 24 * 60 * 60 * 1000


def sent_today(last_sent_at: Optional[int], now: datetime) -> bool:
    return last_sent_at is not None and last_sent_at >= day_start_ms(now)


def should_send(
    now: datetime,
    *,
    enabled: bool,
    quota: int,
    last_sent_at: Optional[int],
    last_reviewed_at: Optional[int],
    created_at: Optional[int],
    quiet_start: int,
    quiet_end: int,
) -> bool:
    """单用户是否应在本窗口发送（纯函数，便于单测）。"""
    if not enabled or quota <= 0:
        return False
    if in_quiet_hours(now, quiet_start, quiet_end):
        return False
    if sent_today(last_sent_at, now):
        return False
    if is_downgraded(now, last_reviewed_at, created_at) and now.weekday() != 0:
        return False
    return True


def build_message_data(due_count: int, now: datetime) -> Dict[str, Any]:
    """构造订阅消息 data（字段名与文案集中在此，与真实模板保持一致）。"""
    return {
        TEMPLATE_FIELD_TITLE: {"value": "错题复习提醒"},
        TEMPLATE_FIELD_COUNT: {"value": due_count},
        TEMPLATE_FIELD_TIME: {"value": now.strftime("%H:%M")},
        TEMPLATE_FIELD_TIP: {"value": "点击进入按到期顺序复习"},
    }


class ReminderScheduler:
    """每日复习提醒调度：start/shutdown 跟随应用生命周期。"""

    def __init__(
        self,
        settings: Settings,
        wechat_service: WechatService,
        session_factory: Optional[sessionmaker[Session]] = None,
    ) -> None:
        self._settings = settings
        self._wechat = wechat_service
        self._session_factory = session_factory
        self._scheduler: Optional[BackgroundScheduler] = None

    def _factory(self) -> sessionmaker[Session]:
        return self._session_factory or get_session_factory()

    def start(self) -> bool:
        """启动调度器；未配置提醒时静默返回 False。"""
        if self._scheduler is not None:
            return False
        if not self._settings.reminder_ready:
            _logger.info("复习提醒未配置（开关/模板 ID/微信密钥），调度器不启动")
            return False

        timezone = resolve_timezone(self._settings.reminder_timezone)
        scheduler = BackgroundScheduler(timezone=timezone)
        scheduler.add_job(
            self.run_tick,
            IntervalTrigger(minutes=TICK_MINUTES, timezone=timezone),
            id="review-reminder",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
        scheduler.start()
        self._scheduler = scheduler
        _logger.info(
            "复习提醒调度已启动：%02d:00 窗口，时区 %s",
            self._settings.reminder_hour,
            self._settings.reminder_timezone,
        )
        return True

    def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    def run_tick(self, now: Optional[datetime] = None) -> Dict[str, int]:
        """执行一次扫描发送；返回统计用于日志/单测。"""
        stats = {"dueUsers": 0, "sent": 0, "skipped": 0, "failed": 0}
        settings = self._settings
        if not settings.reminder_ready:
            return stats

        timezone = resolve_timezone(settings.reminder_timezone)
        now_local = now or datetime.now(timezone)
        if now_local.tzinfo is None:
            now_local = now_local.replace(tzinfo=timezone)

        if not in_reminder_window(now_local, settings.reminder_hour):
            return stats
        if in_quiet_hours(
            now_local, settings.reminder_quiet_start, settings.reminder_quiet_end
        ):
            return stats

        session = self._factory()()
        try:
            due_rows = (
                session.query(QuestionSync.user_id, func.count(QuestionSync.id))
                .filter(
                    QuestionSync.deleted.is_(False),
                    QuestionSync.next_review_at.isnot(None),
                    QuestionSync.next_review_at < day_end_ms(now_local),
                )
                .group_by(QuestionSync.user_id)
                .all()
            )
            stats["dueUsers"] = len(due_rows)

            for user_id, due_count in due_rows:
                self._handle_user(session, user_id, int(due_count), now_local, stats)
        finally:
            session.close()
        return stats

    def _handle_user(
        self,
        session: Session,
        user_id: int,
        due_count: int,
        now_local: datetime,
        stats: Dict[str, int],
    ) -> bool:
        """处理单个用户；返回 True 表示已完成一次发送。"""
        settings = self._settings
        subscription = (
            session.query(ReminderSubscription)
            .filter(ReminderSubscription.user_id == user_id)
            .one_or_none()
        )
        user = session.get(User, user_id)
        last_reviewed_at = (
            session.query(func.max(QuestionSync.last_reviewed_at))
            .filter(
                QuestionSync.user_id == user_id,
                QuestionSync.deleted.is_(False),
            )
            .scalar()
        )

        if user is None or subscription is None or not should_send(
            now_local,
            enabled=bool(subscription.enabled),
            quota=int(subscription.quota or 0),
            last_sent_at=subscription.last_sent_at,
            last_reviewed_at=last_reviewed_at,
            created_at=user.created_at if user is not None else None,
            quiet_start=settings.reminder_quiet_start,
            quiet_end=settings.reminder_quiet_end,
        ):
            stats["skipped"] += 1
            return False

        # 抢占式幂等：仅当今日尚未发送且状态仍满足时更新成功才真正发送
        sent_at = int(now_local.timestamp() * 1000)
        claimed = (
            session.query(ReminderSubscription)
            .filter(
                ReminderSubscription.user_id == user_id,
                ReminderSubscription.enabled.is_(True),
                ReminderSubscription.quota > 0,
                or_(
                    ReminderSubscription.last_sent_at.is_(None),
                    ReminderSubscription.last_sent_at < day_start_ms(now_local),
                ),
            )
            .update({"last_sent_at": sent_at}, synchronize_session=False)
        )
        session.commit()
        if not claimed:
            stats["skipped"] += 1
            return False

        result: SendMessageResult = self._wechat.send_subscribe_message(
            user.openid,
            settings.reminder_template_id,
            build_message_data(due_count, now_local),
            settings.reminder_page,
        )
        if not result.ok:
            # 失败只记日志、不重试；last_sent_at 已占用当日名额
            _logger.warning("复习提醒发送失败 user=%s: %s", user_id, result.reason)
            stats["failed"] += 1
            return True

        session.query(ReminderSubscription).filter(
            ReminderSubscription.user_id == user_id,
            ReminderSubscription.quota > 0,
        ).update(
            {"quota": ReminderSubscription.quota - 1}, synchronize_session=False
        )
        session.commit()
        stats["sent"] += 1
        return True
