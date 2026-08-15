import telebot
from telebot.apihelper import ApiTelegramException
from sqlalchemy import func, desc

from utils.helpers import (
    is_group,
    is_admin,
    build_user_mention,
    escape_html,
    extract_target_and_reason,
    extract_user_id,
)

from db import get_session
from models import Warn, ChatSetting
from groups.logs import log_action


DEFAULT_MAX = 3


def get_max_warns_for_chat(chat_id: int) -> int:
    s = get_session()
    try:
        setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(chat_id)).first()
        if setting and setting.max_warns:
            return max(1, int(setting.max_warns))
        return DEFAULT_MAX
    finally:
        s.close()


def warn_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["warn"])
    def warn(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        target, reason, err = extract_target_and_reason(bot, message)
        if err:
            return bot.reply_to(message, err)

        if not target:
            return bot.reply_to(message, "کاربر مشخص نیست.")

        s = get_session()
        try:
            w = Warn(chat_id=str(message.chat.id), user_id=target.id, reason=reason)
            s.add(w)
            s.commit()

            count = s.query(Warn).filter(Warn.chat_id == str(message.chat.id), Warn.user_id == target.id).count()
            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")

            text = (
                f"کاربر {name} هشدار دریافت کرد.\n"
                f"تعداد Warn: {count}\n"
                f"دلیل: {escape_html(reason)}\n"
                f"توسط: {admin_name}"
            )

            bot.reply_to(message, text, parse_mode="HTML")

            # log warn
            try:
                log_action(
                    action="warn",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target.id,
                    details=reason,
                )
            except Exception:
                pass

            max_warns = get_max_warns_for_chat(message.chat.id)
            if count >= max_warns:
                try:
                    bot.kick_chat_member(message.chat.id, target.id)
                    bot.send_message(
                        message.chat.id,
                        f"کاربر {name} به‌خاطر رسیدن به حداکثر Warn ({max_warns}) حذف شد.",
                        parse_mode="HTML",
                    )
                    # پاک‌سازی warns for this user
                    s.query(Warn).filter(Warn.chat_id == str(message.chat.id), Warn.user_id == target.id).delete()
                    s.commit()
                    try:
                        log_action(
                            action="auto_kick_on_max_warn",
                            chat_id=message.chat.id,
                            admin_id=message.from_user.id,
                            target_id=target.id,
                            details=f"max_warns={max_warns}",
                        )
                    except Exception:
                        pass
                except ApiTelegramException as e:
                    bot.reply_to(message, f"خطا هنگام اعمال اکشن: {e}")
        finally:
            s.close()


    @bot.message_handler(commands=["unwarn"])
    def unwarn(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        s = get_session()
        try:
            # remove last warn
            last = (
                s.query(Warn)
                .filter(Warn.chat_id == str(message.chat.id), Warn.user_id == user_id)
                .order_by(Warn.ts.desc())
                .first()
            )
            if not last:
                return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")
            s.delete(last)
            s.commit()
            bot.reply_to(message, "Warn کاربر کاهش یافت یا حذف شد.")
        finally:
            s.close()


    @bot.message_handler(commands=["warns"])
    def show_warns(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        parts = message.text.split()
        s = get_session()
        try:
            if len(parts) > 1 and parts[1].lstrip("-").isdigit():
                user_id = int(parts[1])
                rows = (
                    s.query(Warn)
                    .filter(Warn.chat_id == str(message.chat.id), Warn.user_id == user_id)
                    .order_by(Warn.ts)
                    .all()
                )
                if not rows:
                    return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")
                text = f"Warns: {len(rows)}\nدلایل:\n"
                for i, r in enumerate(rows, 1):
                    text += f"{i}. {escape_html(r.reason or '')}\n"
                return bot.reply_to(message, text, parse_mode="HTML")

            # otherwise list top warners
            rows = (
                s.query(Warn.user_id, func.count(Warn.id).label("cnt"))
                .filter(Warn.chat_id == str(message.chat.id))
                .group_by(Warn.user_id)
                .order_by(desc("cnt"))
                .limit(20)
                .all()
            )
            if not rows:
                return bot.reply_to(message, "هیچ وارنتی ثبت نشده.")
            text = "لیست کاربران دارای Warn:\n"
            for uid, count in rows:
                text += f"ID: <code>{uid}</code> — {count}\n"
            return bot.reply_to(message, text, parse_mode="HTML")
        finally:
            s.close()


    @bot.message_handler(commands=["set_max_warns"])
    def set_max_warns(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return bot.reply_to(message, "استفاده: /set_max_warns <تعداد>\nمثال: /set_max_warns 3")

        value = int(parts[1])
        if value < 1:
            return bot.reply_to(message, "حداقل باید 1 یا بیشتر باشد.")

        s = get_session()
        try:
            setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(message.chat.id)).first()
            if not setting:
                setting = ChatSetting(chat_id=str(message.chat.id), max_warns=value)
                s.add(setting)
            else:
                setting.max_warns = value
            s.commit()
            bot.reply_to(message, f"حداکثر Warn برای این گروه تنظیم شد به: {value}")
        finally:
            s.close()
