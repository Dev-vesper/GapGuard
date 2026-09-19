"""قفل انواع محتوا برای کل گروه یا برای یک کاربر خاص."""

import telebot
from telebot.apihelper import ApiTelegramException

from bot.guards import command_guard
from bot.helpers import build_user_mention, escape_html, extract_user_id, is_group
from services.log_service import log_action
from services.restrict_service import (
    ALLOWED_CONTENT_TYPES,
    add_restriction,
    is_content_locked,
    is_valid_content_type,
    list_restrictions,
    remove_restriction,
)
from services.stats_service import track_message


def _delete_message(bot: telebot.TeleBot, message) -> None:
    """حذف پیام متخلف + ثبت لاگ."""
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except ApiTelegramException:
        pass
    log_action(
        action="auto_delete_content_restriction",
        chat_id=message.chat.id,
        target_id=message.from_user.id,
        details=f"type={message.content_type}",
    )


def restrict_handler(bot: telebot.TeleBot):

    # ──────────────────────────────────────────────
    #  /restrict_content — قفل انواع محتوا برای کل گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["restrict_content"])
    def restrict_content(message):
        err = command_guard(
            bot, message,
            restrict_error="ربات دسترسی لازم برای قفل محتوا را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(
                message,
                "استفاده:\n"
                "/restrict_content add|remove|list <نوع>\n\n"
                "انواع موجود:\n" + "\n".join(
                    f"  <code>{k}</code> — {v}" for k, v in ALLOWED_CONTENT_TYPES.items()
                ),
                parse_mode="HTML",
            )

        action = parts[1].lower()

        if action == "list":
            locked = list_restrictions(message.chat.id)
            if not locked:
                return bot.reply_to(message, "هیچ محتوایی قفل نشده است.")
            text = "محتواهای قفل‌شده در گروه:\n" + "\n".join(
                f"  🔒 <code>{t}</code> — {ALLOWED_CONTENT_TYPES.get(t, t)}"
                for t in locked
            )
            return bot.reply_to(message, text, parse_mode="HTML")

        if len(parts) < 3:
            return bot.reply_to(message, "نوع محتوا را مشخص کنید.")

        content_type = parts[2].strip().lower()

        if action == "add":
            if not is_valid_content_type(content_type):
                return bot.reply_to(
                    message,
                    f"نوع نامعتبر: <code>{escape_html(content_type)}</code>\n"
                    "انواع مجاز: " + ", ".join(ALLOWED_CONTENT_TYPES.keys()),
                    parse_mode="HTML",
                )
            if not add_restriction(message.chat.id, content_type):
                return bot.reply_to(message, "این نوع محتوا قبلا قفل شده است.")
            log_action(
                action="restrict_content_add",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                details=content_type,
            )
            return bot.reply_to(
                message,
                f"🔒 نوع محتوای <code>{escape_html(content_type)}</code> قفل شد.",
                parse_mode="HTML",
            )

        if action == "remove":
            if not remove_restriction(message.chat.id, content_type):
                return bot.reply_to(message, "این نوع محتوا قفل نبوده است.")
            log_action(
                action="restrict_content_remove",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                details=content_type,
            )
            return bot.reply_to(
                message,
                f"🔓 نوع محتوای <code>{escape_html(content_type)}</code> از قفل خارج شد.",
                parse_mode="HTML",
            )

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")

    # ──────────────────────────────────────────────
    #  /restrict_user_content — قفل محتوا برای کاربر خاص
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["restrict_user_content"])
    def restrict_user_content(message):
        err = command_guard(
            bot, message,
            restrict_error="ربات دسترسی لازم برای قفل محتوای کاربر را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(
                message,
                "استفاده:\n"
                "/restrict_user_content add|remove|list <نوع> <reply|user_id>\n\n"
                "انواع موجود:\n" + "\n".join(
                    f"  <code>{k}</code> — {v}" for k, v in ALLOWED_CONTENT_TYPES.items()
                ),
                parse_mode="HTML",
            )

        action = parts[1].lower()

        if action == "list":
            # لیست محتواهای قفل‌شده برای یک کاربر
            target_id, err_id = extract_user_id(message)
            if err_id:
                return bot.reply_to(message, "کاربر را ریپلای کنید یا ID وارد کنید.")
            locked = list_restrictions(message.chat.id, user_id=target_id)
            if not locked:
                return bot.reply_to(
                    message,
                    f"هیچ محتوایی برای کاربر <code>{target_id}</code> قفل نشده است.",
                    parse_mode="HTML",
                )
            text = f"محتواهای قفل‌شده برای کاربر <code>{target_id}</code>:\n" + "\n".join(
                f"  🔒 <code>{t}</code> — {ALLOWED_CONTENT_TYPES.get(t, t)}"
                for t in locked
            )
            return bot.reply_to(message, text, parse_mode="HTML")

        if len(parts) < 3:
            return bot.reply_to(message, "نوع محتوا را مشخص کنید.")

        content_type = parts[2].strip().lower()

        if not is_valid_content_type(content_type):
            return bot.reply_to(
                message,
                f"نوع نامعتبر: <code>{escape_html(content_type)}</code>\n"
                "انواع مجاز: " + ", ".join(ALLOWED_CONTENT_TYPES.keys()),
                parse_mode="HTML",
            )

        # استخراج کاربر از ریپلای یا سومین آرگومان
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        else:
            # سومین آرگومان باید user_id باشد
            parts_full = message.text.split()
            if len(parts_full) >= 4 and parts_full[3].lstrip("-").isdigit():
                target_id = int(parts_full[3])

        if not target_id:
            return bot.reply_to(message, "کاربر را ریپلای کنید یا ID وارد کنید.")

        # تلاش برای دریافت اطلاعات کاربر
        try:
            member = bot.get_chat_member(message.chat.id, target_id)
            user_name = build_user_mention(member.user)
        except ApiTelegramException:
            user_name = f"<code>{target_id}</code>"

        if action == "add":
            if not add_restriction(message.chat.id, content_type, user_id=target_id):
                return bot.reply_to(
                    message,
                    f"این نوع محتوا قبلا برای کاربر {user_name} قفل شده است.",
                    parse_mode="HTML",
                )
            log_action(
                action="restrict_user_content_add",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                target_id=target_id,
                details=content_type,
            )
            return bot.reply_to(
                message,
                f"🔒 نوع محتوای <code>{escape_html(content_type)}</code> برای کاربر {user_name} قفل شد.",
                parse_mode="HTML",
            )

        if action == "remove":
            if not remove_restriction(message.chat.id, content_type, user_id=target_id):
                return bot.reply_to(
                    message,
                    f"این نوع محتوا قفل نبوده است.",
                )
            log_action(
                action="restrict_user_content_remove",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                target_id=target_id,
                details=content_type,
            )
            return bot.reply_to(
                message,
                f"🔓 نوع محتوای <code>{escape_html(content_type)}</code> برای کاربر {user_name} از قفل خارج شد.",
                parse_mode="HTML",
            )

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")

    # ──────────────────────────────────────────────
    #  /my_restrictions — نمایش قفل‌های کاربر جاری
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["my_restrictions"])
    def my_restrictions(message):
        if not is_group(message):
            return

        locked = list_restrictions(message.chat.id, user_id=message.from_user.id)
        group_locked = list_restrictions(message.chat.id)

        if not locked and not group_locked:
            return bot.reply_to(message, "هیچ محتوایی برای شما قفل نشده است.")

        lines = []
        if locked:
            lines.append("🔒 قفل‌های شخصی شما:")
            for t in locked:
                lines.append(f"  • {ALLOWED_CONTENT_TYPES.get(t, t)}")
        if group_locked:
            lines.append("\n🔒 قفل‌های گروه:")
            for t in group_locked:
                lines.append(f"  • {ALLOWED_CONTENT_TYPES.get(t, t)}")

        return bot.reply_to(message, "\n".join(lines))

    # ──────────────────────────────────────────────
    #  اجرای خودکار قفل محتوا روی پیام‌ها
    # ──────────────────────────────────────────────
    # یک هندلر مخصوص نوع محتوا ثبت می‌کنیم (نه catch-all) تا پیش از
    # هندلر catch-all ماژول filter اجرا شود.
    _LOCKED_TYPES = [
        "photo", "video", "sticker", "animation", "voice",
        "video_note", "document", "audio",
    ]

    @bot.message_handler(content_types=_LOCKED_TYPES)
    def enforce_content_lock(message):
        if not is_group(message):
            return

        # شمارش پیام برای آمارگیری
        track_message(message)

        user_id = message.from_user.id
        ctype = message.content_type

        if is_content_locked(message.chat.id, user_id, ctype):
            _delete_message(bot, message)
            try:
                type_label = ALLOWED_CONTENT_TYPES.get(ctype, ctype)
                bot.send_message(
                    message.chat.id,
                    f"⚠️ {build_user_mention(message.from_user)}، ارسال <b>{escape_html(type_label)}</b> در این گروه مجاز نیست.",
                    parse_mode="HTML",
                )
            except ApiTelegramException:
                pass
