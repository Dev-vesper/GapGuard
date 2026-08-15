import telebot
from telebot.apihelper import ApiTelegramException


# استفاده از ماژول هلپر برای راحتیه کار
from utils.helpers import (
    is_group,
    is_admin,
    bot_can_restrict,
    escape_html,
    build_user_mention,
    extract_target_and_reason
)
from groups.logs import log_action


def ban_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["ban"])
    def ban(message):
        if not is_group(message): # یه نمونه از استفاده از is_group
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
                "ربات دسترسی Ban کردن کاربران را ندارد."
            )

        target, reason, err = extract_target_and_reason(bot, message)
        if err:
            return bot.reply_to(message, err)

        if target.id == bot_info.id:
            return bot.reply_to(message, "نمی‌توانم خودم را Ban کنم.")

        try:
            target_member = bot.get_chat_member(message.chat.id, target.id)
            if target_member.status in ("administrator", "creator"):
                return bot.reply_to(
                    message,
                    "نمی‌توان ادمین یا Owner گروه را Ban کرد."
                )
        except ApiTelegramException:
            return bot.reply_to(message, "خطا در بررسی وضعیت کاربر.")

        try:
            bot.ban_chat_member(
                chat_id=message.chat.id,
                user_id=target.id
            )

            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")
            reason_safe = escape_html(reason)

            bot.reply_to(
                message,
                (
                    "کاربر Ban شد\n\n"
                    f"کاربر: {name}\n"
                    f"ID: <code>{target.id}</code>\n"
                    f"دلیل: {reason_safe}\n"
                    f"توسط: {admin_name}"
                ),
                parse_mode="HTML"
            )
            # log the ban
            try:
                log_action(
                    action="ban",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target.id,
                    details=reason,
                )
            except Exception:
                pass

        except ApiTelegramException as e:
            desc = (e.description or str(e)).lower()
            if "not enough rights" in desc:
                msg = "ربات دسترسی کافی برای Ban کردن ندارد."
            elif "administrator" in desc:
                msg = "نمی‌توان ادمین را Ban کرد."
            elif "user not found" in desc:
                msg = "کاربر پیدا نشد."
            else:
                msg = f"خطا هنگام Ban کردن کاربر:\n<code>{e}</code>"
            return bot.reply_to(message, msg, parse_mode="HTML")

        except Exception as e:
            return bot.reply_to(
                message,
                f"خطای غیرمنتظره:\n<code>{e}</code>",
                parse_mode="HTML"
            )
