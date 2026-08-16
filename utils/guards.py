"""گاردهای مشترک دستورات مدیریتی و قالب‌های پیام/خطا."""

from typing import Optional

import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import Message, User

from utils.helpers import (
    is_group,
    is_admin,
    bot_can_restrict,
    escape_html,
    build_user_mention,
)


def command_guard(
    bot: telebot.TeleBot,
    message: Message,
    restrict_error: Optional[str] = None,
) -> Optional[str]:
    """چک‌های مشترک همه دستورات مدیریتی؛ در صورت رد، پیام خطا برمی‌گرداند."""
    if not is_group(message):
        return "این دستور فقط در گروه قابل استفاده است."
    if not is_admin(bot, message.chat.id, message.from_user.id):
        return "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند."
    if restrict_error is not None:
        bot_info = bot.get_me()
        if not bot_can_restrict(bot, message.chat.id, bot_info.id):
            return restrict_error
    return None


def target_guard(
    bot: telebot.TeleBot,
    chat_id: int,
    target: User,
    action: str,
) -> Optional[str]:
    """جلوگیری از اکشن روی خود ربات یا ادمین‌های گروه."""
    bot_info = bot.get_me()
    if target.id == bot_info.id:
        return f"نمی‌توانم خودم را {action} کنم."
    try:
        member = bot.get_chat_member(chat_id, target.id)
    except ApiTelegramException:
        return "خطا در بررسی وضعیت کاربر."
    if member.status in ("administrator", "creator"):
        return f"نمی‌توان ادمین یا Owner گروه را {action} کرد."
    return None


def action_report(
    title: str,
    target: User,
    admin: User,
    reason: Optional[str] = None,
) -> str:
    """قالب مشترک پیام موفقیت اکشن‌های مدیریتی (HTML)."""
    lines = [
        f"کاربر {title} شد",
        "",
        f"کاربر: {build_user_mention(target)}",
        f"ID: <code>{target.id}</code>",
    ]
    if reason is not None:
        lines.append(f"دلیل: {escape_html(reason)}")
    lines.append(f"توسط: {escape_html(admin.first_name or 'Unknown')}")
    return "\n".join(lines)


def api_error_text(action: str, e: Exception) -> str:
    """تبدیل ApiTelegramException به پیام فارسی (HTML-safe)."""
    desc = (getattr(e, "description", None) or str(e)).lower()
    if "not enough rights" in desc:
        return f"ربات دسترسی کافی برای {action} کردن ندارد."
    if "administrator" in desc:
        return f"نمی‌توان ادمین را {action} کرد."
    if "user not found" in desc:
        return "کاربر پیدا نشد."
    if "chat not found" in desc:
        return "گروه پیدا نشد."
    return f"خطا هنگام {action} کردن کاربر:\n<code>{escape_html(str(e))}</code>"


def unexpected_error_text(e: Exception) -> str:
    return f"خطای غیرمنتظره:\n<code>{escape_html(str(e))}</code>"
