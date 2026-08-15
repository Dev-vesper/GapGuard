import telebot
from telebot.apihelper import ApiTelegramException


def unban_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unban"])
    def unban(message):

        # فقط گروه
        if message.chat.type not in ("group", "supergroup"):
            return bot.reply_to(
                message,
                "❌ این دستور فقط در گروه قابل استفاده است."
            )

        # بررسی ادمین اجراکننده
        try:
            admin = bot.get_chat_member(
                message.chat.id,
                message.from_user.id
            )

            if admin.status not in ("administrator", "creator"):
                return bot.reply_to(
                    message,
                    "❌ فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
                )

        except ApiTelegramException:
            return bot.reply_to(
                message,
                "❌ خطا در بررسی دسترسی شما."
            )

        # بررسی دسترسی ربات
        try:
            bot_info = bot.get_me()

            bot_member = bot.get_chat_member(
                message.chat.id,
                bot_info.id
            )

            if (
                bot_member.status != "creator"
                and not getattr(
                    bot_member,
                    "can_restrict_members",
                    False
                )
            ):
                return bot.reply_to(
                    message,
                    "❌ ربات دسترسی لازم برای Unban کردن کاربران را ندارد."
                )

        except ApiTelegramException:
            return bot.reply_to(
                message,
                "❌ خطا در بررسی دسترسی ربات."
            )

        # -------------------------
        # تعیین User ID
        # -------------------------

        user_id = None

        # Reply
        if message.reply_to_message:

            user_id = message.reply_to_message.from_user.id

        # User ID
        else:

            parts = message.text.split()

            if len(parts) < 2:
                return bot.reply_to(
                    message,
                    (
                        "⚠️ کاربر مشخص نشده.\n\n"
                        "روش استفاده:\n"
                        "• Reply → /unban\n"
                        "• /unban USER_ID"
                    )
                )

            user_id = parts[1]

            if not user_id.lstrip("-").isdigit():
                return bot.reply_to(
                    message,
                    "❌ User ID نامعتبر است."
                )

            user_id = int(user_id)

        # -------------------------
        # Unban
        # -------------------------

        try:

            bot.unban_chat_member(
                chat_id=message.chat.id,
                user_id=user_id,
                only_if_banned=True
            )

            bot.reply_to(
                message,
                (
                    "✅ <b>کاربر Unban شد</b>\n\n"
                    f"🆔 <b>ID:</b> "
                    f"<code>{user_id}</code>\n"
                    f"👮 <b>توسط:</b> "
                    f"{message.from_user.first_name}"
                ),
                parse_mode="HTML"
            )

        except ApiTelegramException as e:

            error = str(e).lower()

            if "not enough rights" in error:
                error_message = (
                    "❌ ربات دسترسی کافی برای Unban کردن ندارد."
                )

            elif "user not found" in error:
                error_message = (
                    "❌ کاربر پیدا نشد."
                )

            elif "chat not found" in error:
                error_message = (
                    "❌ گروه پیدا نشد."
                )

            else:
                error_message = (
                    "❌ خطا هنگام Unban کردن کاربر:\n"
                    f"<code>{e}</code>"
                )

            return bot.reply_to(
                message,
                error_message,
                parse_mode="HTML"
            )

        except Exception as e:

            return bot.reply_to(
                message,
                (
                    "❌ خطای غیرمنتظره:\n"
                    f"<code>{e}</code>"
                ),
                parse_mode="HTML"
            )