"""تنظیمات هر گروه — تنها منبع خواندن و نوشتن ChatSetting."""

from dataclasses import dataclass

from core.database import session_scope
from database import repositories as repo

DEFAULT_MAX_WARNS = 3


@dataclass(frozen=True)
class ChatSettings:
    """عکس فوری و بی‌وابسته از تنظیمات گروه (بدون نشتی ORM به لایه هندلر)."""

    max_warns: int = DEFAULT_MAX_WARNS
    auto_remove_banned: bool = True
    anti_link: bool = False
    anti_forward: bool = False


def get_chat_settings(chat_id) -> ChatSettings:
    """تنظیمات گروه؛ در نبود رکورد، مقادیر پیش‌فرض برمی‌گردد."""
    with session_scope() as session:
        row = repo.get_setting(session, chat_id)
        if row is None:
            return ChatSettings()
        return ChatSettings(
            max_warns=row.max_warns or DEFAULT_MAX_WARNS,
            auto_remove_banned=bool(row.auto_remove_banned),
            anti_link=bool(row.anti_link),
            anti_forward=bool(row.anti_forward),
        )


def update_chat_settings(chat_id, **fields) -> None:
    """ساخت یا به‌روزرسانی تنظیمات گروه با فیلدهای داده‌شده."""
    with session_scope() as session:
        repo.upsert_setting(session, chat_id, **fields)
