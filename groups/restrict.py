"""قفل انواع محتوا و قفل محتوا برای کاربر خاص."""

import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, escape_html, build_user_mention, extract_user_id
from utils.guards import command_guard
from groups.logs import log_action
from groups.stats import track_message
from db import get_session
from models import ContentRestriction

ALLOWED_CONTENT_TYPES = {
    "photo": "عکس",
    "video": "ویدیو",
    "sticker": "استیکر",
    "animation": "گیف",
    "voice": "ویس",
    "video_note": "ویدیو نوت",
    "document": "فایل",
    "audio": "آدیو",
    "poll": "نظرسنجی",
    "contact": "کانتکت",
    "location": "لوکیشن",
}


def _get_restrictions(chat_id: int, user_id: int = None):
    """لیست محتواهای قفل‌شده را برمی‌گرداند."""
    s = get_session()
    try:
        q = s.query(ContentRestriction).filter(
            ContentRestriction.chat_id == str(chat_id)
        )
        if user_id is not None:
            q = q.filter(ContentRestriction.user_id == user_id)
        else:
            q = q.filter(ContentRestriction.user_id.is_(None))
        return [r.content_type for r in q.all()]
    finally:
        s.close()


def _add_restriction(chat_id: int, content_type: str, user_id: int = None) -> bool:
    """افزودن قفل محتوا. False اگر قبلا وجود داشته باشد."""
    s = get_session()
    try:
        q = s.query(ContentRestriction).filter(
            ContentRestriction.chat_id == str(chat_id),
            ContentRestriction.content_type == content_type,
        )
        if user_id is not None:
            q = q.filter(ContentRestriction.user_id == user_id)
        else:
            q = q.filter(ContentRestriction.user_id.is_(None))
        if q.first():
            return False
        s.add(
            ContentRestriction(
                chat_id=str(chat_id), user_id=user_id, content_type=content_type
            )
        )
        s.commit()
        return True
    finally:
        s.close()


def _remove_restriction(chat_id: int, content_type: str, user_id: int = None) -> bool:
    """حذف قفل محتوا. False اگر وجود نداشته باشد."""
    s = get_session()
    try:
        q = s.query(ContentRestriction).filter(
            ContentRestriction.chat_id == str(chat_id),
            ContentRestriction.content_type == content_type,
        )
        if user_id is not None:
            q = q.filter(ContentRestriction.user_id == user_id)
        else:
            q = q.filter(ContentRestriction.user_id.is_(None))
        count = q.delete()
        s.commit()
        return count > 0
    finally:
        s.close()


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


def _message_is_restricted(
    chat_id: int, user_id: int, content_type: str
) -> bool:
    """بررسی می‌کند آیا این نوع محتوا قفل است یا نه."""
    # قفل کاربر خاص — اگر هیچ محدودیتی برای او ثبت شده باشد
    user_restrictions = _get_restrictions(chat_id, user_id=user_id)
    if content_type in user_restrictions:
        return True
    # قفل کل گروه
    group_restrictions = _get_restrictions(chat_id, user_id=None)
    if content_type in group_restrictions:
        return True
    return False


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
            locked = _get_restrictions(message.chat.id)
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
            if content_type not in ALLOWED_CONTENT_TYPES:
                return bot.reply_to(
                    message,
                    f"نوع نامعتبر: <code>{escape_html(content_type)}</code>\n"
                    "انواع مجاز: " + ", ".join(ALLOWED_CONTENT_TYPES.keys()),
                    parse_mode="HTML",
                )
            if not _add_restriction(message.chat.id, content_type):
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
            if not _remove_restriction(message.chat.id, content_type):
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
            locked = _get_restrictions(message.chat.id, user_id=target_id)
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

        if content_type not in ALLOWED_CONTENT_TYPES:
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
            if not _add_restriction(message.chat.id, content_type, user_id=target_id):
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
            if not _remove_restriction(message.chat.id, content_type, user_id=target_id):
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

        locked = _get_restrictions(message.chat.id, user_id=message.from_user.id)
        group_locked = _get_restrictions(message.chat.id, user_id=None)

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
    # ما هندلر جداگانه‌ای ثبت نمی‌کنیم چون filter.py یک catch-all
    # handler ثبت می‌کند. به‌جای آن، logic اجرا در هندلر scan_message
    # filter.py ادغام می‌شود (فیلتر اعمال می‌شود قبل از آن هندلر).
    #
    # اما برای سادگی و عدم نیاز به تغییر filter.py، یک هندلر
    # content-type-specific ثبت می‌کنیم که قبل از catch-all اجرا شود.
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

        if _message_is_restricted(message.chat.id, user_id, ctype):
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
