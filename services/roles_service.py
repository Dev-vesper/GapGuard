"""منطق ممبرهای ویژه، تگ‌ها و ارتقای اعضا."""

import telebot

from core.database import session_scope
from database import repositories as repo


def list_special_members(chat_id) -> list:
    with session_scope() as session:
        return repo.list_special_members(session, chat_id)


def add_special_member(chat_id, user_id: int) -> None:
    with session_scope() as session:
        repo.add_special_member(session, chat_id, user_id)


def remove_special_member(chat_id, user_id: int) -> None:
    with session_scope() as session:
        repo.remove_special_member(session, chat_id, user_id)


def list_tags(chat_id) -> dict:
    with session_scope() as session:
        return repo.list_tags(session, chat_id)


def set_tag(chat_id, user_id: int, tag_text: str) -> None:
    with session_scope() as session:
        repo.set_tag(session, chat_id, user_id, tag_text)


def remove_tag(chat_id, user_id: int) -> None:
    with session_scope() as session:
        repo.remove_tag(session, chat_id, user_id)


def promote_member(bot: telebot.TeleBot, chat_id: int, user_id: int) -> None:
    """ارتقا با دسترسی‌های محدود (بدون حق ارتقای دیگران)."""
    bot.promote_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        can_change_info=False,
        can_post_messages=False,
        can_edit_messages=False,
        can_delete_messages=False,
        can_invite_users=True,
        can_restrict_members=True,
        can_pin_messages=True,
        can_promote_members=False,
    )
