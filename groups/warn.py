import os
import json
from typing import Tuple, Optional

import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import (
    is_group,
    is_admin,
    build_user_mention,
    escape_html,
    extract_target_and_reason,
    extract_user_id,
)


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
WARNS_FILE = os.path.join(DATA_DIR, "warns.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
DEFAULT_MAX = 3


def _load_settings() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_settings(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_max_warns_for_chat(chat_id: int) -> int:
    settings = _load_settings()
    chat_settings = settings.get(str(chat_id), {})
    try:
        v = int(chat_settings.get("max_warns", DEFAULT_MAX))
        return max(1, v)
    except Exception:
        return DEFAULT_MAX



def _ensure_storage():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _load_warns() -> dict:
    _ensure_storage()
    try:
        with open(WARNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_warns(data: dict):
    _ensure_storage()
    with open(WARNS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_user_entry(data: dict, chat_id: int, user_id: int) -> dict:
    chat = data.setdefault(str(chat_id), {})
    return chat.setdefault(str(user_id), {"count": 0, "reasons": []})


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

        try:
            data = _load_warns()
            entry = _get_user_entry(data, message.chat.id, target.id)
            entry["count"] = entry.get("count", 0) + 1
            entry.setdefault("reasons", []).append(reason or "بدون دلیل")
            _save_warns(data)

            count = entry["count"]
            name = build_user_mention(target)
            admin_name = escape_html(message.from_user.first_name or "Unknown")

            text = (
                f"کاربر {name} هشدار دریافت کرد.\n"
                f"تعداد Warn: {count}\n"
                f"دلیل: {escape_html(reason)}\n"
                f"توسط: {admin_name}"
            )

            bot.reply_to(message, text, parse_mode="HTML")

            # اعمال اقدام در صورت رسیدن به حد (قابل تنظیم برای هر گروه)
            max_warns = get_max_warns_for_chat(message.chat.id)
            if count >= max_warns:
                try:
                    bot.kick_chat_member(message.chat.id, target.id)
                    bot.send_message(
                        message.chat.id,
                        f"کاربر {name} به‌خاطر رسیدن به حداکثر Warn ({max_warns}) حذف شد.",
                        parse_mode="HTML"
                    )
                    # پاک‌سازی رکورد بعد از اعمال
                    data = _load_warns()
                    chat = data.get(str(message.chat.id), {})
                    if str(target.id) in chat:
                        del chat[str(target.id)]
                        _save_warns(data)
                except ApiTelegramException as e:
                    bot.reply_to(message, f"خطا هنگام اعمال اکشن: {e}")

        except Exception as e:
            return bot.reply_to(message, f"خطا: {e}")


    @bot.message_handler(commands=["unwarn"])
    def unwarn(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        # allow both reply and id
        user_id, err = extract_user_id(message)
        if err:
            return bot.reply_to(message, err)

        try:
            data = _load_warns()
            chat = data.get(str(message.chat.id), {})
            entry = chat.get(str(user_id))
            if not entry:
                return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")

            # decrease by 1, or remove
            if entry.get("count", 0) <= 1:
                del chat[str(user_id)]
            else:
                entry["count"] = entry.get("count", 1) - 1
                reasons = entry.get("reasons", [])
                if reasons:
                    reasons.pop()

            data[str(message.chat.id)] = chat
            _save_warns(data)

            bot.reply_to(message, "Warn کاربر کاهش یافت یا حذف شد.")

        except Exception as e:
            return bot.reply_to(message, f"خطا: {e}")


    @bot.message_handler(commands=["warns"])
    def show_warns(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        parts = message.text.split()
        # optional: show for specific user
        if len(parts) > 1:
            user_id_str = parts[1]
            if not user_id_str.lstrip("-").isdigit():
                return bot.reply_to(message, "ایدی نامعتبره")
            user_id = int(user_id_str)
            data = _load_warns()
            chat = data.get(str(message.chat.id), {})
            entry = chat.get(str(user_id))
            if not entry:
                return bot.reply_to(message, "هیچ وارنتی برای این کاربر وجود ندارد.")
            text = f"Warns: {entry.get('count',0)}\nدلایل:\n"
            for i, r in enumerate(entry.get("reasons", []), 1):
                text += f"{i}. {escape_html(r)}\n"
            return bot.reply_to(message, text, parse_mode="HTML")

        # otherwise list top warners (small list)
        data = _load_warns()
        chat = data.get(str(message.chat.id), {})
        if not chat:
            return bot.reply_to(message, "هیچ وارنتی ثبت نشده.")
        items = []
        for uid, entry in chat.items():
            items.append((int(uid), entry.get("count", 0)))
        items.sort(key=lambda x: x[1], reverse=True)
        text = "لیست کاربران دارای Warn:\n"
        for uid, count in items[:20]:
            text += f"ID: <code>{uid}</code> — {count}\n"
        return bot.reply_to(message, text, parse_mode="HTML")


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

        settings = _load_settings()
        chat = settings.setdefault(str(message.chat.id), {})
        chat["max_warns"] = value
        _save_settings(settings)
        bot.reply_to(message, f"حداکثر Warn برای این گروه تنظیم شد به: {value}")
