"""فیلتر پیام‌ها: کلمات ممنوعه، لینک و فوروارد."""

import telebot
from telebot.apihelper import ApiTelegramException

from bot.guards import command_guard
from bot.helpers import is_group
from services.filter_service import (
    add_banned_word,
    contains_link,
    find_banned_word,
    is_forwarded,
    list_banned_words,
    remove_banned_word,
)
from services.log_service import log_action
from services.settings_service import get_chat_settings
from services.stats_service import track_message


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
            words = list_banned_words(message.chat.id)
            if not words:
                return bot.reply_to(message, "هیچ کلمه‌ای فیلتر نشده.")
            return bot.reply_to(message, "فیلتر شده‌ها:\n" + "\n".join(words))

        if len(parts) < 3:
            return bot.reply_to(message, "کلمه را مشخص کنید.")

        word = parts[2].strip().lower()

        if action == "add":
            if not add_banned_word(message.chat.id, word):
                return bot.reply_to(message, "این کلمه قبلا اضافه شده.")
            return bot.reply_to(message, "کلمه اضافه شد.")

        if action == "remove":
            remove_banned_word(message.chat.id, word)
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

        settings = get_chat_settings(message.chat.id)

        word = find_banned_word(text, list_banned_words(message.chat.id))
        if word:
            if settings.auto_remove_banned:
                _auto_delete(bot, message, f"word:{word}")
            return

        if settings.anti_link and contains_link(text):
            _auto_delete(bot, message, "anti_link")
            return

        if settings.anti_forward and is_forwarded(message):
            _auto_delete(bot, message, "anti_forward")
