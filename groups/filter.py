import re
from typing import List

import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group
from utils.guards import command_guard
from groups.logs import log_action
from groups.settings import get_chat_setting
from groups.stats import track_message
from db import get_session
from models import BannedWord


LINK_PATTERN = re.compile(r"https?://|t\.me/|telegram\.me/")


def _get_banned_words(chat_id: int) -> List[str]:
    s = get_session()
    try:
        rows = s.query(BannedWord).filter(BannedWord.chat_id == str(chat_id)).all()
        return [r.word for r in rows]
    finally:
        s.close()


def _add_banned_word(chat_id: int, word: str) -> bool:
    s = get_session()
    try:
        exists = (
            s.query(BannedWord)
            .filter(BannedWord.chat_id == str(chat_id), BannedWord.word == word)
            .first()
        )
        if exists:
            return False
        s.add(BannedWord(chat_id=str(chat_id), word=word))
        s.commit()
        return True
    finally:
        s.close()


def _remove_banned_word(chat_id: int, word: str):
    s = get_session()
    try:
        s.query(BannedWord).filter(
            BannedWord.chat_id == str(chat_id), BannedWord.word == word
        ).delete()
        s.commit()
    finally:
        s.close()


def _auto_delete(bot: telebot.TeleBot, message, reason: str) -> None:
    """حذف خودکار پیام + ثبت لاگ؛ اگر حذف ناموفق باشد بی‌صدا رد می‌شود."""
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except ApiTelegramException:
        return
    log_action(
        action="auto_delete",
        chat_id=message.chat.id,
        target_id=message.from_user.id,
        details=f"reason={reason}",
    )


def filter_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["banword"])
    def banword(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(message, "استفاده: /banword add|remove|list <word>")
        action = parts[1].lower()

        if action == "list":
            words = _get_banned_words(message.chat.id)
            if not words:
                return bot.reply_to(message, "هیچ کلمه‌ای فیلتر نشده.")
            return bot.reply_to(message, "فیلتر شده‌ها:\n" + "\n".join(words))

        if len(parts) < 3:
            return bot.reply_to(message, "کلمه را مشخص کنید.")

        word = parts[2].strip().lower()

        if action == "add":
            if not _add_banned_word(message.chat.id, word):
                return bot.reply_to(message, "این کلمه قبلا اضافه شده.")
            return bot.reply_to(message, "کلمه اضافه شد.")

        if action == "remove":
            _remove_banned_word(message.chat.id, word)
            return bot.reply_to(message, "کلمه حذف شد.")

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")

    @bot.message_handler(func=lambda m: True, content_types=["text", "caption"])
    def scan_message(message):
        # دستورات ربات اسکن نمی‌شوند (مثلاً خودِ کلمه فیلترشده در /banword)
        if not is_group(message):
            return

        # شمارش پیام متنی برای آمارگیری
        track_message(message)

        text = (message.text or message.caption or "").lower()
        if not text or text.startswith("/"):
            return

        setting = get_chat_setting(message.chat.id)
        auto_remove = True if not setting else setting.auto_remove_banned
        anti_link = False if not setting else setting.anti_link
        anti_forward = False if not setting else setting.anti_forward

        for w in _get_banned_words(message.chat.id):
            if w and re.search(r"\b" + re.escape(w) + r"\b", text):
                if auto_remove:
                    _auto_delete(bot, message, f"word:{w}")
                return

        if anti_link and LINK_PATTERN.search(text):
            _auto_delete(bot, message, "anti_link")
            return

        if anti_forward and getattr(message, "forward_from", None) is not None:
            _auto_delete(bot, message, "anti_forward")
