"""قواعد قفل انواع محتوا برای کل گروه یا برای یک کاربر خاص."""

from typing import List, Optional

from core.database import session_scope
from database import repositories as repo

ALLOWED_CONTENT_TYPES = {
    "photo": "عکس",
    "video": "ویدیو",
    "sticker": "استیکر",
    "animation": "گیف",
    "voice": "ویس",
    "video_note": "ویدیو نوت",
    "document": "فایل",
    "audio": "آدیو",
    "poll": "نظرسنجی",
    "contact": "کانتکت",
    "location": "لوکیشن",
}


def list_restrictions(chat_id, user_id: Optional[int] = None) -> List[str]:
    """نوع محتواهای قفل‌شده برای یک کاربر یا برای کل گروه."""
    with session_scope() as session:
        return repo.list_restrictions(session, chat_id, user_id)


def add_restriction(chat_id, content_type: str, user_id: Optional[int] = None) -> bool:
    """False اگر این قفل از قبل وجود داشته باشد."""
    with session_scope() as session:
        return repo.add_restriction(session, chat_id, content_type, user_id)


def remove_restriction(chat_id, content_type: str, user_id: Optional[int] = None) -> bool:
    """False اگر این قفل وجود نداشته باشد."""
    with session_scope() as session:
        return repo.remove_restriction(session, chat_id, content_type, user_id)


def is_valid_content_type(content_type: str) -> bool:
    return content_type in ALLOWED_CONTENT_TYPES


def is_content_locked(chat_id, user_id: int, content_type: str) -> bool:
    """قفل شخصی کاربر یا قفل کل گروه."""
    if content_type in list_restrictions(chat_id, user_id=user_id):
        return True
    return content_type in list_restrictions(chat_id, user_id=None)
