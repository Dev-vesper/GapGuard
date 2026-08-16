import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import extract_target_and_reason
from utils.guards import (
    command_guard,
    target_guard,
    action_report,
    api_error_text,
    unexpected_error_text,
)
from groups.logs import log_action


def ban_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["ban"])
    def ban(message):
        err = command_guard(
            bot, message, restrict_error="ربات دسترسی Ban کردن کاربران را ندارد."
        )
        if err:
            return bot.reply_to(message, err)

        target, reason, err = extract_target_and_reason(bot, message)
        if err:
            return bot.reply_to(message, err)

        err = target_guard(bot, message.chat.id, target, "Ban")
        if err:
            return bot.reply_to(message, err)

        try:
            bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id)
        except ApiTelegramException as e:
            return bot.reply_to(message, api_error_text("Ban", e), parse_mode="HTML")
        except Exception as e:
            return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

        bot.reply_to(
            message,
            action_report("Ban", target, message.from_user, reason),
            parse_mode="HTML",
        )
        log_action(
            action="ban",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=target.id,
            details=reason,
        )
