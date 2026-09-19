"""ثبت و بازیابی لاگ اکشن‌های مدیریتی."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core.database import session_scope
from core.logger import get_logger
from database import repositories as repo

logger = get_logger(__name__)

PER_PAGE = 10


@dataclass(frozen=True)
class LogEntry:
    ts: datetime
    action: str
    admin_id: Optional[int]
    target_id: Optional[int]
    details: Optional[str]


def log_action(
    action: str,
    chat_id,
    admin_id: Optional[int] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    """درج لاگ؛ خطا هرگز اجرای دستور اصلی را متوقف نمی‌کند."""
    try:
        with session_scope() as session:
            repo.insert_log(session, action, chat_id, admin_id, target_id, details)
    except Exception:
        logger.exception("log_action failed: action=%s chat=%s", action, chat_id)


def list_logs(action: Optional[str] = None, page: int = 1) -> List[LogEntry]:
    with session_scope() as session:
        rows = repo.list_logs(session, action, page, PER_PAGE)
        return [
            LogEntry(row.ts, row.action, row.admin_id, row.target_id, row.details)
            for row in rows
        ]
