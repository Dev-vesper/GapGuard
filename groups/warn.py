import telebot
from telebot.apihelper import ApiTelegramException
from sqlalchemy import func, desc

from utils.helpers import (
    build_user_mention,
    escape_html,
    extract_target_and_reason,
    extract_user_id,
)
from utils.guards import command_guard

from db import get_session
from models import Warn
from groups.logs import log_action
from groups.settings import get_chat_setting


DEFAULT_MAX = 3


def get_max_warns_for_chat(chat_id: int) -> int:
    setting = get_chat_setting(chat_id)
    if setting and setting.max_warns:
        return max(1, int(setting.max_warns))
    return DEFAULT_MAX


def warn_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["warn"])
    def warn(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        target, reason, err = extract_target_and_reason(bot, message)
        if err:
            return bot.reply_to(message, err)

        if not target:
            return bot.reply_to(message, "کاربر مشخص نیست.")

        s = get_session()
        try:
            s.add(Warn(chat_id=str(message.chat.id), user_id=target.id, reason=reason))
            s.commit()

            count = (
                s.query(Warn)
                .filter(Warn.chat_id == str(message.chat.id), Warn.user_id == target.id)
                .count()
            )
            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")

            bot.reply_to(
                message,
                (
                    f"کاربر {name} هشدار دریافت کرد.\n"
                    f"تعداد Warn: {count}\n"
                    f"دلیل: {escape_html(reason)}\n"
                    f"توسط: {admin_name}"
                ),
                parse_mode="HTML",
            )
            log_action(
                action="warn",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                target_id=target.id,
                details=reason,
            )

            max_warns = get_max_warns_for_chat(message.chat.id)
            if count >= max_warns:
                try:
                    bot.kick_chat_member(message.chat.id, target.id)
                    bot.send_message(
                        message.chat.id,
                        f"کاربر {name} به‌خاطر رسیدن به حداکثر Warn ({max_warns}) حذف شد.",
                        parse_mode="HTML",
                    )
                    # پاک‌سازی وارن‌های کاربر پس از kick
                    s.query(Warn).filter(
                        Warn.chat_id == str(message.chat.id),
                        Warn.user_id == target.id,
                    ).delete()
                    s.commit()
                    log_action(
                        action="auto_kick_on_max_warn",
                        chat_id=message.chat.id,
                        admin_id=message.from_user.id,
                        target_id=target.id,
                        details=f"max_warns={max_warns}",
                    )
                except ApiTelegramException as e:
                    bot.reply_to(message, f"خطا هنگام اعمال اکشن: {e}")
        finally:
            s.close()

    @bot.message_handler(commands=["unwarn"])
    def unwarn(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        s = get_session()
        try:
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
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

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

            # بدون آرگومان: برترین وارن‌گیرندگان گروه
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
