"""دستورات مدیریت اعضا: بن، آنبن، کیک، میوت، آنمیوت و سیستم اخطار."""

import telebot
from telebot.apihelper import ApiTelegramException

from bot.guards import (
    action_report,
    api_error_text,
    command_guard,
    target_guard,
    unexpected_error_text,
)
from bot.helpers import (
    build_user_mention,
    escape_html,
    extract_target_and_reason,
    extract_user_id,
)
from services.log_service import log_action
from services.moderation_service import (
    ban_member,
    clear_warns,
    kick_member,
    max_warns_for_chat,
    mute_member,
    remove_last_warn,
    top_warned,
    unban_member,
    unmute_member,
    warn_member,
    warns_of,
)


def _run_target_action(bot, message, *, label, restrict_error, run) -> None:
    """جریان مشترک ban/kick/mute — تنها تفاوتشان اکشن و برچسب است."""
    err = command_guard(bot, message, restrict_error=restrict_error)
    if err:
        return bot.reply_to(message, err)

    target, reason, err = extract_target_and_reason(bot, message)
    if err:
        return bot.reply_to(message, err)

    err = target_guard(bot, message.chat.id, target, label)
    if err:
        return bot.reply_to(message, err)

    try:
        run(bot, message.chat.id, target.id)
    except ApiTelegramException as e:
        return bot.reply_to(message, api_error_text(label, e), parse_mode="HTML")
    except Exception as e:
        return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

    bot.reply_to(
        message,
        action_report(label, target, message.from_user, reason),
        parse_mode="HTML",
    )
    log_action(
        action=label.lower(),
        chat_id=message.chat.id,
        admin_id=message.from_user.id,
        target_id=target.id,
        details=reason,
    )


def moderation_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["ban"])
    def ban(message):
        _run_target_action(
            bot,
            message,
            label="Ban",
            restrict_error="ربات دسترسی Ban کردن کاربران را ندارد.",
            run=ban_member,
        )

    @bot.message_handler(commands=["unban"])
    def unban(message):
        err = command_guard(
            bot,
            message,
            restrict_error="ربات دسترسی لازم برای Unban کردن کاربران را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            unban_member(bot, message.chat.id, user_id)
        except ApiTelegramException as e:
            return bot.reply_to(message, api_error_text("Unban", e), parse_mode="HTML")
        except Exception as e:
            return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

        bot.reply_to(
            message,
            (
                "کاربر Unban شد\n\n"
                f"ID: <code>{user_id}</code>\n"
                f"توسط: {escape_html(message.from_user.first_name or 'Unknown')}"
            ),
            parse_mode="HTML",
        )
        log_action(
            action="unban",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=user_id,
        )

    @bot.message_handler(commands=["kick"])
    def kick(message):
        _run_target_action(
            bot,
            message,
            label="Kick",
            restrict_error="ربات دسترسی Kick کردن کاربران را ندارد.",
            run=kick_member,
        )

    @bot.message_handler(commands=["mute"])
    def mute(message):
        _run_target_action(
            bot,
            message,
            label="Mute",
            restrict_error="ربات دسترسی Mute کردن کاربران را ندارد.",
            run=mute_member,
        )

    @bot.message_handler(commands=["unmute"])
    def unmute(message):
        err = command_guard(
            bot,
            message,
            restrict_error="ربات دسترسی لازم برای Unmute کردن کاربران را ندارد.",
        )
        if err:
            return bot.reply_to(message, err)

        target_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            target = bot.get_chat_member(message.chat.id, target_id).user
        except ApiTelegramException:
            return bot.reply_to(message, "کاربری با این ID در گروه پیدا نشد.")

        try:
            unmute_member(bot, message.chat.id, target_id)
        except ApiTelegramException as e:
            return bot.reply_to(message, api_error_text("Unmute", e), parse_mode="HTML")
        except Exception as e:
            return bot.reply_to(message, unexpected_error_text(e), parse_mode="HTML")

        bot.reply_to(
            message,
            (
                "Mute کاربر برداشته شد\n\n"
                f"کاربر: {build_user_mention(target)}\n"
                f"ID: <code>{target.id}</code>\n"
                f"توسط: {escape_html(message.from_user.first_name or 'Unknown')}"
            ),
            parse_mode="HTML",
        )
        log_action(
            action="unmute",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=target_id,
        )

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

        count = warn_member(message.chat.id, target.id, reason)
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

        max_warns = max_warns_for_chat(message.chat.id)
        if count >= max_warns:
            try:
                kick_member(bot, message.chat.id, target.id)
                bot.send_message(
                    message.chat.id,
                    f"کاربر {name} به‌خاطر رسیدن به حداکثر Warn ({max_warns}) حذف شد.",
                    parse_mode="HTML",
                )
                clear_warns(message.chat.id, target.id)
                log_action(
                    action="auto_kick_on_max_warn",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=target.id,
                    details=f"max_warns={max_warns}",
                )
            except ApiTelegramException as e:
                bot.reply_to(message, f"خطا هنگام اعمال اکشن: {e}")

    @bot.message_handler(commands=["unwarn"])
    def unwarn(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        if not remove_last_warn(message.chat.id, user_id):
            return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")
        bot.reply_to(message, "Warn کاربر کاهش یافت یا حذف شد.")

    @bot.message_handler(commands=["warns"])
    def show_warns(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        if len(parts) > 1 and parts[1].lstrip("-").isdigit():
            user_id = int(parts[1])
            reasons = warns_of(message.chat.id, user_id)
            if not reasons:
                return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")
            text = f"Warns: {len(reasons)}\nدلایل:\n"
            for i, reason in enumerate(reasons, 1):
                text += f"{i}. {escape_html(reason or '')}\n"
            return bot.reply_to(message, text, parse_mode="HTML")

        rows = top_warned(message.chat.id)
        if not rows:
            return bot.reply_to(message, "هیچ وارنتی ثبت نشده.")
        text = "لیست کاربران دارای Warn:\n"
        for user_id, count in rows:
            text += f"ID: <code>{user_id}</code> — {count}\n"
        return bot.reply_to(message, text, parse_mode="HTML")
