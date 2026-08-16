import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import extract_user_id, unmute_permissions, build_user_mention, escape_html
from utils.guards import command_guard, api_error_text, unexpected_error_text
from groups.logs import log_action


def unmute_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unmute"])
    def unmute(message):
        err = command_guard(
            bot, message,
            restrict_error="ربات دسترسی لازم برای Unmute کردن کاربران را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        target_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            target = bot.get_chat_member(message.chat.id, target_id).user
        except ApiTelegramException:
            return bot.reply_to(message, "کاربری با این ID در گروه پیدا نشد.")

        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_id,
                permissions=unmute_permissions(),
            )
        except ApiTelegramException as e:
            return bot.reply_to(message, api_error_text("Unmute", e), parse_mode="HTML")
        except Exception as e:
            return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

        bot.reply_to(
            message,
            (
                "Mute کاربر برداشته شد\n\n"
                f"کاربر: {build_user_mention(target)}\n"
                f"ID: <code>{target.id}</code>\n"
                f"توسط: {escape_html(message.from_user.first_name or 'Unknown')}"
            ),
            parse_mode="HTML",
        )
        log_action(
            action="unmute",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=target_id,
        )
