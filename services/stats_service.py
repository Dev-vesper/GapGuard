"""منطق آمارگیری: ثبت پیام، حل بازه زمانی و تجمیع آمار."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from core.database import session_scope
from core.logger import get_logger
from database import repositories as repo

logger = get_logger(__name__)

PERIODS = ("today", "week", "month")


def _now() -> datetime:
    return datetime.utcnow()


def _today_start() -> datetime:
    return _now().replace(hour=0, minute=0, second=0, microsecond=0)


def _days_ago_start(days: int) -> datetime:
    return _today_start() - timedelta(days=days)


def resolve_period(parts: List[str]) -> Tuple[Optional[datetime], str]:
    """بازه زمانی و برچسبش را از آرگومان دستور استخراج می‌کند.

    تنها جای این منطق است؛ پیش‌تر پنج بار عیناً در هندلرهای آمار کپی شده بود.
    """
    period = "all"
    if len(parts) >= 2 and parts[1].lower() in PERIODS:
        period = parts[1].lower()

    if period == "today":
        return _today_start(), "امروز"
    if period == "week":
        return _days_ago_start(7), "۷ روز اخیر"
    if period == "month":
        return _days_ago_start(30), "۳۰ روز اخیر"
    return None, "کل دوره"


def track_message(message) -> None:
    """ثبت یک پیام برای آمارگیری؛ خطا هرگز پردازش پیام را متوقف نمی‌کند."""
    try:
        with session_scope() as session:
            repo.add_message_stat(
                session,
                message.chat.id,
                message.from_user.id,
                message.content_type,
                _now(),
            )
    except Exception:
        logger.exception("track_message failed: chat=%s", message.chat.id)


@dataclass(frozen=True)
class GroupStats:
    period_label: str
    total_messages: int
    active_users: int
    total_warns: int
    mod_actions: int
    banned_words: int
    content_locks: int


@dataclass(frozen=True)
class UserStats:
    total: int
    today: int
    week: int
    warns: int
    peak_hour: Optional[int]
    peak_day: Optional[int]
    content: List[Tuple[str, int]]


def group_stats(chat_id, since: Optional[datetime], period_label: str) -> GroupStats:
    with session_scope() as session:
        return GroupStats(
            period_label=period_label,
            total_messages=repo.count_messages(session, chat_id, since=since),
            active_users=repo.count_active_users(session, chat_id, since=since),
            total_warns=repo.count_warns(session, chat_id, since=since),
            mod_actions=repo.count_logs(session, chat_id, since=since),
            banned_words=repo.count_banned_words(session, chat_id),
            content_locks=repo.count_restrictions(session, chat_id),
        )


def user_stats(chat_id, user_id: int) -> UserStats:
    with session_scope() as session:
        hours = repo.time_breakdown(session, chat_id, "hour", user_id=user_id)
        days = repo.time_breakdown(session, chat_id, "dow", user_id=user_id)
        content = repo.content_breakdown(session, chat_id, user_id=user_id)
        return UserStats(
            total=repo.count_messages(session, chat_id, user_id=user_id),
            today=repo.count_messages(
                session, chat_id, user_id=user_id, since=_today_start()
            ),
            week=repo.count_messages(
                session, chat_id, user_id=user_id, since=_days_ago_start(7)
            ),
            warns=repo.count_warns(session, chat_id, user_id=user_id),
            peak_hour=int(hours[0][0]) if hours else None,
            peak_day=int(days[0][0]) if days else None,
            content=[(ctype, cnt) for ctype, cnt in content],
        )


def top_members(
    chat_id, since: Optional[datetime], limit: int = 15
) -> List[Tuple[int, int]]:
    with session_scope() as session:
        return [
            (user_id, count)
            for user_id, count in repo.top_members(
                session, chat_id, since=since, limit=limit
            )
        ]


def content_stats(
    chat_id, since: Optional[datetime]
) -> List[Tuple[str, int]]:
    with session_scope() as session:
        return [
            (content_type, count)
            for content_type, count in repo.content_breakdown(
                session, chat_id, since=since
            )
        ]


def hourly_stats(chat_id, since: Optional[datetime]) -> Dict[int, int]:
    """تعداد پیام به تفکیک ساعت شبانه‌روز."""
    with session_scope() as session:
        rows = repo.time_breakdown(
            session, chat_id, "hour", since=since, order_by_count=False
        )
        return {int(hour): count for hour, count in rows}


def moderation_stats(
    chat_id, since: Optional[datetime]
) -> List[Tuple[str, int]]:
    with session_scope() as session:
        return [
            (action, count)
            for action, count in repo.action_breakdown(session, chat_id, since=since)
        ]


def reset_message_stats(chat_id) -> int:
    with session_scope() as session:
        return repo.reset_message_stats(session, chat_id)
