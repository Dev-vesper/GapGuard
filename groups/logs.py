import telebot
from sqlalchemy import desc

from utils.guards import command_guard
from db import get_session
from models import Log


def log_action(
    action: str,
    chat_id: int,
    admin_id: int = None,
    target_id: int = None,
    details: str = None,
):
    """درج رکورد در جدول logs؛ خطاها داخلی مدیریت می‌شوند تا اجرای دستور اصلی متوقف نشود."""
    s = get_session()
    try:
        s.add(Log(
            action=action,
            chat_id=str(chat_id),
            admin_id=admin_id,
            target_id=target_id,
            details=details,
        ))
        s.commit()
    except Exception:
        s.rollback()
    finally:
        s.close()


def logs_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["logs"])
    def show_logs(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        filter_action = None
        page = 1
        if len(parts) >= 2:
            if parts[1].isdigit():
                page = int(parts[1])
            else:
                filter_action = parts[1].lower()
        if len(parts) >= 3 and parts[2].isdigit():
            page = int(parts[2])

        s = get_session()
        try:
            q = s.query(Log)
            if filter_action:
                q = q.filter(Log.action == filter_action)
            q = q.order_by(desc(Log.ts))
            per_page = 10
            items = q.offset((page - 1) * per_page).limit(per_page).all()
            if not items:
                return bot.reply_to(message, "صفحه‌ای وجود ندارد یا لاگی یافت نشد.")
            text = f"لاگ‌ها (صفحه {page}):\n"
            for e in items:
                ts = e.ts.isoformat()
                a = e.action
                admin = e.admin_id
                target = e.target_id
                details = e.details or ""
                text += f"[{ts}] {a} admin:{admin} target:{target} {details}\n"
            bot.reply_to(message, text)
        finally:
            s.close()
