import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import (
    is_group,
    is_admin,
    bot_can_restrict,
    escape_html,
    extract_user_id
)


def unban_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unban"])
    def unban(message):
        if not is_group(message):
            return bot.reply_to(
                message,
                "این دستور فقط در گروه قابل استفاده است."
            )

        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(
                message,
                "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
            )

        bot_info = bot.get_me()

        if not bot_can_restrict(bot, message.chat.id, bot_info.id):
            return bot.reply_to(
                message,
                "ربات دسترسی لازم برای Unban کردن کاربران را ندارد."
            )

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            bot.unban_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                only_if_banned=True
            )

            admin_name = escape_html(message.from_user.first_name or "Unknown")

            bot.reply_to(
                message,
                (
                    "کاربر Unban شد\n\n"
                    f"ID: <code>{user_id}</code>\n"
                    f"توسط: {admin_name}"
                ),
                parse_mode="HTML"
            )

        except ApiTelegramException as e:
            desc = (e.description or str(e)).lower()
            if "not enough rights" in desc:
                msg = "ربات دسترسی کافی برای Unban کردن ندارد."
            elif "user not found" in desc:
                msg = "کاربر پیدا نشد."
            elif "chat not found" in desc:
                msg = "گروه پیدا نشد."
            else:
                msg = f"خطا هنگام Unban کردن کاربر:\n<code>{e}</code>"
            return bot.reply_to(message, msg, parse_mode="HTML")

        except Exception as e:
            return bot.reply_to(
                message,
                f"خطای غیرمنتظره:\n<code>{e}</code>",
                parse_mode="HTML"
            )
