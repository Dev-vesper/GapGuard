import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import (
    is_group,
    is_admin,
    bot_can_restrict,
    escape_html,
    build_user_mention,
    extract_user_id,
    unmute_permissions
)


def unmute_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unmute"])
    def unmute(message):
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
                "ربات دسترسی لازم برای Unmute کردن کاربران را ندارد."
            )

        target_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            target_member = bot.get_chat_member(message.chat.id, target_id)
            target = target_member.user
        except ApiTelegramException:
            return bot.reply_to(
                message,
                "کاربری با این ID در گروه پیدا نشد."
            )

        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target_id,
                permissions=unmute_permissions()
            )

            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")

            bot.reply_to(
                message,
                (
                    "Mute کاربر برداشته شد\n\n"
                    f"کاربر: {name}\n"
                    f"ID: <code>{target.id}</code>\n"
                    f"توسط: {admin_name}"
                ),
                parse_mode="HTML"
            )

        except ApiTelegramException as e:
            desc = (e.description or str(e)).lower()
            if "not enough rights" in desc:
                msg = "ربات دسترسی کافی برای Unmute کردن ندارد."
            elif "administrator" in desc:
                msg = "این کاربر ادمین است."
            elif "user not found" in desc:
                msg = "کاربر پیدا نشد."
            elif "chat not found" in desc:
                msg = "گروه پیدا نشد."
            else:
                msg = f"خطا هنگام Unmute کردن کاربر:\n<code>{e}</code>"
            return bot.reply_to(message, msg, parse_mode="HTML")

        except Exception as e:
            return bot.reply_to(
                message,
                f"خطای غیرمنتظره:\n<code>{e}</code>",
                parse_mode="HTML"
            )
