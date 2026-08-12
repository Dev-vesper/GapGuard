import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import (
    is_group,
    is_admin,
    bot_can_restrict,
    escape_html,
    build_user_mention,
    extract_target_and_reason,
    mute_permissions
)


def mute_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["mute"])
    def mute(message):
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
                "ربات دسترسی Mute کردن کاربران را ندارد."
            )

        target, reason, err = extract_target_and_reason(bot, message)
        if err:
            return bot.reply_to(message, err)

        if target.id == bot_info.id:
            return bot.reply_to(message, "نمی‌توانم خودم را Mute کنم.")

        try:
            target_member = bot.get_chat_member(message.chat.id, target.id)
            if target_member.status in ("administrator", "creator"):
                return bot.reply_to(
                    message,
                    "نمی‌توان ادمین یا Owner گروه را Mute کرد."
                )
        except ApiTelegramException:
            return bot.reply_to(message, "خطا در بررسی وضعیت کاربر.")

        try:
            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,
                permissions=mute_permissions()
            )

            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")
            reason_safe = escape_html(reason)

            bot.reply_to(
                message,
                (
                    "کاربر Mute شد\n\n"
                    f"کاربر: {name}\n"
                    f"ID: <code>{target.id}</code>\n"
                    f"دلیل: {reason_safe}\n"
                    f"توسط: {admin_name}"
                ),
                parse_mode="HTML"
            )

        except ApiTelegramException as e:
            desc = (e.description or str(e)).lower()
            if "not enough rights" in desc:
                msg = "ربات دسترسی کافی برای Mute کردن ندارد."
            elif "administrator" in desc:
                msg = "نمی‌توان ادمین را Mute کرد."
            elif "user not found" in desc:
                msg = "کاربر پیدا نشد."
            elif "chat not found" in desc:
                msg = "گروه پیدا نشد."
            else:
                msg = f"خطا هنگام Mute کردن کاربر:\n<code>{e}</code>"
            return bot.reply_to(message, msg, parse_mode="HTML")

        except Exception as e:
            return bot.reply_to(
                message,
                f"خطای غیرمنتظره:\n<code>{e}</code>",
                parse_mode="HTML"
            )
