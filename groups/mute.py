import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import ChatPermissions


def mute_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["mute"])
    def mute(message):

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
                    "❌ ربات دسترسی Mute کردن کاربران را ندارد."
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
        reason = "بدون دلیل"

        # Reply
        if message.reply_to_message:

            target = message.reply_to_message.from_user

            parts = message.text.split(maxsplit=1)

            if len(parts) > 1:
                reason = parts[1]

        # User ID
        else:

            parts = message.text.split(maxsplit=2)

            if len(parts) < 2:
                return bot.reply_to(
                    message,
                    (
                        "⚠️ کاربر مشخص نشده.\n\n"
                        "روش استفاده:\n"
                        "• Reply → /mute دلیل\n"
                        "• /mute USER_ID دلیل"
                    )
                )

            user_id = parts[1]

            if not user_id.lstrip("-").isdigit():
                return bot.reply_to(
                    message,
                    "❌ User ID نامعتبر است."
                )

            if len(parts) == 3:
                reason = parts[2]

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
        # جلوگیری از Mute کردن ربات
        # -------------------------

        try:
            bot_info = bot.get_me()

            if target.id == bot_info.id:
                return bot.reply_to(
                    message,
                    "🤖 نمی‌توانم خودم را Mute کنم."
                )

        except ApiTelegramException:
            pass

        # -------------------------
        # جلوگیری از Mute کردن ادمین
        # -------------------------

        try:
            target_member = bot.get_chat_member(
                message.chat.id,
                target.id
            )

            if target_member.status in (
                "administrator",
                "creator"
            ):
                return bot.reply_to(
                    message,
                    "❌ نمی‌توان ادمین یا Owner گروه را Mute کرد."
                )

        except ApiTelegramException:
            return bot.reply_to(
                message,
                "❌ خطا در بررسی وضعیت کاربر."
            )

        # -------------------------
        # Mute
        # -------------------------

        try:

            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_audios=False,
                can_send_documents=False,
                can_send_photos=False,
                can_send_videos=False,
                can_send_video_notes=False,
                can_send_voice_notes=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
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
                    "🔇 <b>کاربر Mute شد</b>\n\n"
                    f"👤 <b>کاربر:</b> "
                    f"<a href='tg://user?id={target.id}'>"
                    f"{name}</a>\n"
                    f"🆔 <b>ID:</b> "
                    f"<code>{target.id}</code>\n"
                    f"📝 <b>دلیل:</b> {reason}\n"
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
                    "❌ ربات دسترسی کافی برای Mute کردن ندارد."
                )

            elif "administrator" in error:
                error_message = (
                    "❌ نمی‌توان ادمین را Mute کرد."
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
                    "❌ خطا هنگام Mute کردن کاربر:\n"
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