import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import extract_user_id, escape_html
from utils.guards import command_guard, api_error_text, unexpected_error_text
from groups.logs import log_action


def unban_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unban"])
    def unban(message):
        err = command_guard(
            bot, message,
            restrict_error="ربات دسترسی لازم برای Unban کردن کاربران را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            bot.unban_chat_member(
                chat_id=message.chat.id, user_id=user_id, only_if_banned=True
            )
        except ApiTelegramException as e:
            return bot.reply_to(message, api_error_text("Unban", e), parse_mode="HTML")
        except Exception as e:
            return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

        bot.reply_to(
            message,
            (
                "کاربر Unban شد\n\n"
                f"ID: <code>{user_id}</code>\n"
                f"توسط: {escape_html(message.from_user.first_name or 'Unknown')}"
            ),
            parse_mode="HTML",
        )
        log_action(
            action="unban",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=user_id,
        )
