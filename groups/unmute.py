import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import ChatPermissions


def unmute_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["unmute"])
    def unmute(message):

        # فقط گروه
        if message.chat.type not in ("group", "supergroup"):
            return bot.reply_to(
                message,
                "❌ این دستور فقط در گروه قابل استفاده است."
            )

        # -------------------------
        # بررسی ادمین اجراکننده
        # -------------------------

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

        # -------------------------
        # بررسی دسترسی ربات
        # -------------------------

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
                    "❌ ربات دسترسی لازم برای Unmute کردن کاربران را ندارد."
                )

        except ApiTelegramException:
            return bot.reply_to(
                message,
                "❌ خطا در بررسی دسترسی ربات."
            )

        # -------------------------
        # تعیین کاربر هدف
        # -------------------------

        target = None

        # Reply
        if message.reply_to_message:

            target = message.reply_to_message.from_user

        # User ID
        else:

            parts = message.text.split()

            if len(parts) < 2:
                return bot.reply_to(
                    message,
                    (
                        "⚠️ کاربر مشخص نشده.\n\n"
                        "روش استفاده:\n"
                        "• Reply → /unmute\n"
                        "• /unmute USER_ID"
                    )
                )

            user_id = parts[1]

            if not user_id.lstrip("-").isdigit():
                return bot.reply_to(
                    message,
                    "❌ User ID نامعتبر است."
                )

            try:
                target = bot.get_chat_member(
                    message.chat.id,
                    int(user_id)
                ).user

            except ApiTelegramException:
                return bot.reply_to(
                    message,
                    "❌ کاربری با این ID در گروه پیدا نشد."
                )

        # -------------------------
        # Unmute
        # -------------------------

        try:

            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )

            bot.restrict_chat_member(
                chat_id=message.chat.id,
                user_id=target.id,
                permissions=permissions
            )

            name = (
                target.first_name
                or target.last_name
                or "Unknown"
            )

            bot.reply_to(
                message,
                (
                    "🔊 <b>Mute کاربر برداشته شد</b>\n\n"
                    f"👤 <b>کاربر:</b> "
                    f"<a href='tg://user?id={target.id}'>"
                    f"{name}</a>\n"
                    f"🆔 <b>ID:</b> "
                    f"<code>{target.id}</code>\n"
                    f"👮 <b>توسط:</b> "
                    f"{message.from_user.first_name}"
                ),
                parse_mode="HTML"
            )

        # -------------------------
        # Telegram API Error
        # -------------------------

        except ApiTelegramException as e:

            error = str(e).lower()

            if "not enough rights" in error:
                error_message = (
                    "❌ ربات دسترسی کافی برای Unmute کردن ندارد."
                )

            elif "administrator" in error:
                error_message = (
                    "❌ این کاربر ادمین است."
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
                    "❌ خطا هنگام Unmute کردن کاربر:\n"
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