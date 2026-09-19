"""نمایش لاگ اکشن‌های مدیریتی."""

import telebot

from bot.guards import command_guard
from services.log_service import list_logs


def logs_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["logs"])
    def show_logs(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        filter_action = None
        page = 1
        if len(parts) >= 2:
            if parts[1].isdigit():
                page = int(parts[1])
            else:
                filter_action = parts[1].lower()
        if len(parts) >= 3 and parts[2].isdigit():
            page = int(parts[2])

        items = list_logs(filter_action, page)
        if not items:
            return bot.reply_to(message, "صفحه‌ای وجود ندارد یا لاگی یافت نشد.")

        text = f"لاگ‌ها (صفحه {page}):\n"
        for entry in items:
            text += (
                f"[{entry.ts.isoformat()}] {entry.action} "
                f"admin:{entry.admin_id} target:{entry.target_id} "
                f"{entry.details or ''}\n"
            )
        bot.reply_to(message, text)
