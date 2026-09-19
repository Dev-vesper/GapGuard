"""منطق اکشن‌های مدیریتی: بن، آنبن، کیک، میوت، آنمیوت و سیستم اخطار."""

import telebot
from telebot.types import ChatPermissions

from core.database import session_scope
from database import repositories as repo
from services.settings_service import get_chat_settings

DEFAULT_MAX_WARNS = 3


# ── اکشن‌های تلگرام ──────────────────────────────────
def ban_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    bot.ban_chat_member(chat_id=chat_id, user_id=user_id)


def unban_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)


def kick_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    """کیک در تلگرام = بن + آنبن فوری."""
    bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
    bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)


def mute_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    bot.restrict_chat_member(
        chat_id=chat_id, user_id=user_id, permissions=_mute_permissions()
    )


def unmute_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    bot.restrict_chat_member(
        chat_id=chat_id, user_id=user_id, permissions=_unmute_permissions()
    )


def _mute_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
    )


def _unmute_permissions() -> ChatPermissions:
    return ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
    )


# ── سیستم اخطار ──────────────────────────────────────
def warn_member(chat_id: int, user_id: int, reason: str) -> int:
    """ثبت اخطار و برگرداندن تعداد اخطارهای فعلی کاربر (شامل همین اخطار)."""
    with session_scope() as session:
        repo.add_warn(session, chat_id, user_id, reason)
        # autoflush خاموش است، پس بدون flush شمارش رکورد جدید را نمی‌بیند
        session.flush()
        return repo.count_warns(session, chat_id, user_id)


def max_warns_for_chat(chat_id: int) -> int:
    max_warns = get_chat_settings(chat_id).max_warns
    if max_warns:
        return max(1, int(max_warns))
    return DEFAULT_MAX_WARNS


def clear_warns(chat_id: int, user_id: int) -> int:
    """پاک‌سازی اخطارهای کاربر (پس از کیک خودکار)."""
    with session_scope() as session:
        return repo.delete_user_warns(session, chat_id, user_id)


def remove_last_warn(chat_id: int, user_id: int) -> bool:
    """حذف آخرین اخطار کاربر. False اگر اخطاری وجود نداشته باشد."""
    with session_scope() as session:
        row = repo.last_warn(session, chat_id, user_id)
        if row is None:
            return False
        repo.delete_warn(session, row)
        return True


def warns_of(chat_id: int, user_id: int):
    """دلیل اخطارهای یک کاربر به ترتیب زمان."""
    with session_scope() as session:
        return [row.reason for row in repo.list_warns(session, chat_id, user_id)]


def top_warned(chat_id: int, limit: int = 20):
    """پراخطارترین کاربران گروه به‌صورت [(user_id, count)]."""
    with session_scope() as session:
        return [(uid, count) for uid, count in repo.top_warned(session, chat_id, limit)]
