"""توابع کمکی خالص: بررسی نوع چت، ساخت منشن و متن، و پارس تارگت."""

import html
from typing import Optional, Tuple

import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import Message, User


def is_group(message: Message) -> bool:
    return message.chat.type in ("group", "supergroup")


def escape_html(text: Optional[str]) -> str:
    return html.escape(text or "")


def build_user_mention(user: User) -> str:
    name = user.first_name or user.last_name or "Unknown"
    name = escape_html(name)
    return f'<a href="tg://user?id={user.id}">{name}</a>'


def extract_target_and_reason(
    bot: telebot.TeleBot,
    message: Message
) -> Tuple[Optional[User], str, Optional[str]]:
    target = None
    reason = "بدون دلیل"
    error = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            reason = parts[1].strip() or reason
    else:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return None, "", "کاربر مشخص نیست"
        user_id_str = parts[1]
        if not user_id_str.lstrip("-").isdigit():
            return None, "", "ایدی نامعتبره"
        if len(parts) == 3:
            reason = parts[2].strip() or reason
        try:
            target = bot.get_chat_member(
                message.chat.id,
                int(user_id_str)
            ).user
        except ApiTelegramException:
            return None, "", "کاربر پیدا نشد"

    return target, reason, error


def extract_user_id(message: Message) -> Tuple[Optional[int], Optional[str]]:
    if message.reply_to_message:
        return message.reply_to_message.from_user.id, None

    parts = message.text.split()
    if len(parts) < 2:
        return None, "کاربر مشخص نیست"
    user_id_str = parts[1]
    if not user_id_str.lstrip("-").isdigit():
        return None, "ایدی نامعتبره"
    return int(user_id_str), None
