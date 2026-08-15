import os
import json
import re
from typing import List

import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, is_admin


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")


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


def _get_banned_words(chat_id: int) -> List[str]:
    settings = _load_settings()
    chat = settings.get(str(chat_id), {})
    return chat.get("banned_words", [])


def _set_banned_words(chat_id: int, words: List[str]):
    settings = _load_settings()
    chat = settings.setdefault(str(chat_id), {})
    chat["banned_words"] = words
    _save_settings(settings)


def filter_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["banword"])
    def banword(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        parts = message.text.split(maxsplit=2)
        if len(parts) < 2:
            return bot.reply_to(message, "استفاده: /banword add|remove|list <word>")
        action = parts[1].lower()

        if action == "list":
            words = _get_banned_words(message.chat.id)
            if not words:
                return bot.reply_to(message, "هیچ کلمه‌ای فیلتر نشده.")
            return bot.reply_to(message, "فیلتر شده‌ها:\n" + "\n".join(words))

        if len(parts) < 3:
            return bot.reply_to(message, "کلمه را مشخص کنید.")

        word = parts[2].strip().lower()
        words = _get_banned_words(message.chat.id)

        if action == "add":
            if word in words:
                return bot.reply_to(message, "این کلمه قبلا اضافه شده.")
            words.append(word)
            _set_banned_words(message.chat.id, words)
            return bot.reply_to(message, "کلمه اضافه شد.")

        if action == "remove":
            if word not in words:
                return bot.reply_to(message, "این کلمه در لیست نیست.")
            words.remove(word)
            _set_banned_words(message.chat.id, words)
            return bot.reply_to(message, "کلمه حذف شد.")

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")


    @bot.message_handler(func=lambda m: True, content_types=["text", "caption"])
    def scan_message(message):
        if not is_group(message):
            return

        text = (message.text or message.caption or "").lower()
        if not text:
            return

        settings = _load_settings()
        chat = settings.get(str(message.chat.id), {})
        auto_remove = chat.get("auto_remove_banned", True)
        anti_link = chat.get("anti_link", False)
        anti_forward = chat.get("anti_forward", False)

        # banned words
        words = chat.get("banned_words", [])
        for w in words:
            if w and re.search(r"\b" + re.escape(w) + r"\b", text):
                if auto_remove:
                    try:
                        bot.delete_message(message.chat.id, message.message_id)
                    except ApiTelegramException:
                        pass
                return

        # anti-link: simple detection
        if anti_link:
            if re.search(r"https?://|t.me/|telegram.me/", text):
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                except ApiTelegramException:
                    pass
                return

        # anti-forward
        if anti_forward and getattr(message, "forward_from", None) is not None:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except ApiTelegramException:
                pass
            return


    @bot.message_handler(commands=["set_auto_remove_banned"])
    def set_auto_remove(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        parts = message.text.split()
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            return bot.reply_to(message, "استفاده: /set_auto_remove_banned on|off")
        value = parts[1].lower() == "on"
        settings = _load_settings()
        chat = settings.setdefault(str(message.chat.id), {})
        chat["auto_remove_banned"] = value
        _save_settings(settings)
        bot.reply_to(message, f"auto_remove_banned set to {value}")


    @bot.message_handler(commands=["set_anti_link"])
    def set_anti_link_cmd(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")
        parts = message.text.split()
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            return bot.reply_to(message, "استفاده: /set_anti_link on|off")
        value = parts[1].lower() == "on"
        settings = _load_settings()
        chat = settings.setdefault(str(message.chat.id), {})
        chat["anti_link"] = value
        _save_settings(settings)
        bot.reply_to(message, f"anti_link set to {value}")


    @bot.message_handler(commands=["set_anti_forward"])
    def set_anti_forward_cmd(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")
        parts = message.text.split()
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            return bot.reply_to(message, "استفاده: /set_anti_forward on|off")
        value = parts[1].lower() == "on"
        settings = _load_settings()
        chat = settings.setdefault(str(message.chat.id), {})
        chat["anti_forward"] = value
        _save_settings(settings)
        bot.reply_to(message, f"anti_forward set to {value}")
