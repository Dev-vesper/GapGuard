"""دستورات تنظیمات گروه (مدل ChatSetting)."""

import telebot

from bot.guards import command_guard
from services.settings_service import update_chat_settings

TOGGLE_FLAGS = {
    "set_auto_remove_banned": "auto_remove_banned",
    "set_anti_link": "anti_link",
    "set_anti_forward": "anti_forward",
}


def settings_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["set_max_warns"])
    def set_max_warns(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return bot.reply_to(
                message, "استفاده: /set_max_warns <تعداد>\nمثال: /set_max_warns 3"
            )

        value = int(parts[1])
        if value < 1:
            return bot.reply_to(message, "حداقل باید 1 یا بیشتر باشد.")

        update_chat_settings(message.chat.id, max_warns=value)
        bot.reply_to(message, f"حداکثر Warn برای این گروه تنظیم شد به: {value}")

    @bot.message_handler(commands=list(TOGGLE_FLAGS))
    def toggle_flag(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        # فرم /set_anti_link@MyBot هم پشتیبانی می‌شود
        command = message.text.split()[0].lstrip("/").split("@")[0].lower()
        field = TOGGLE_FLAGS[command]

        parts = message.text.split()
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            return bot.reply_to(message, f"استفاده: /{command} on|off")

        value = parts[1].lower() == "on"
        update_chat_settings(message.chat.id, **{field: value})
        bot.reply_to(message, f"{field} set to {value}")
