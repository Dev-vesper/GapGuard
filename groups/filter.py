import re
from typing import List

import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, is_admin
from groups.logs import log_action
from db import get_session
from models import BannedWord, ChatSetting


def _get_banned_words(chat_id: int) -> List[str]:
    s = get_session()
    try:
        rows = s.query(BannedWord).filter(BannedWord.chat_id == str(chat_id)).all()
        return [r.word for r in rows]
    finally:
        s.close()


def _add_banned_word(chat_id: int, word: str):
    s = get_session()
    try:
        exists = s.query(BannedWord).filter(BannedWord.chat_id == str(chat_id), BannedWord.word == word).first()
        if exists:
            return False
        bw = BannedWord(chat_id=str(chat_id), word=word)
        s.add(bw)
        s.commit()
        return True
    finally:
        s.close()


def _remove_banned_word(chat_id: int, word: str):
    s = get_session()
    try:
        s.query(BannedWord).filter(BannedWord.chat_id == str(chat_id), BannedWord.word == word).delete()
        s.commit()
    finally:
        s.close()


def _get_chat_setting(chat_id: int) -> ChatSetting:
    s = get_session()
    try:
        setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(chat_id)).first()
        return setting
    finally:
        s.close()


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

        if action == "add":
            ok = _add_banned_word(message.chat.id, word)
            if not ok:
                return bot.reply_to(message, "این کلمه قبلا اضافه شده.")
            return bot.reply_to(message, "کلمه اضافه شد.")

        if action == "remove":
            _remove_banned_word(message.chat.id, word)
            return bot.reply_to(message, "کلمه حذف شد.")

        return bot.reply_to(message, "پارامتر نامعتبر: add|remove|list")


    @bot.message_handler(func=lambda m: True, content_types=["text", "caption"])
    def scan_message(message):
        if not is_group(message):
            return

        text = (message.text or message.caption or "").lower()
        if not text:
            return

        setting = _get_chat_setting(message.chat.id)
        auto_remove = True if not setting else setting.auto_remove_banned
        anti_link = False if not setting else setting.anti_link
        anti_forward = False if not setting else setting.anti_forward

        # banned words
        words = _get_banned_words(message.chat.id)
        for w in words:
            if w and re.search(r"\b" + re.escape(w) + r"\b", text):
                if auto_remove:
                    try:
                        bot.delete_message(message.chat.id, message.message_id)
                        try:
                            log_action(
                                action="auto_delete",
                                chat_id=message.chat.id,
                                admin_id=None,
                                target_id=message.from_user.id,
                                details=f"reason=word:{w}",
                            )
                        except Exception:
                            pass
                    except ApiTelegramException:
                        pass
                return

        # anti-link: simple detection
        if anti_link:
            if re.search(r"https?://|t.me/|telegram.me/", text):
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    try:
                        log_action(
                            action="auto_delete",
                            chat_id=message.chat.id,
                            admin_id=None,
                            target_id=message.from_user.id,
                            details="reason=anti_link",
                        )
                    except Exception:
                        pass
                except ApiTelegramException:
                    pass
                return

        # anti-forward
        if anti_forward and getattr(message, "forward_from", None) is not None:
            try:
                bot.delete_message(message.chat.id, message.message_id)
                try:
                    log_action(
                        action="auto_delete",
                        chat_id=message.chat.id,
                        admin_id=None,
                        target_id=message.from_user.id,
                        details="reason=anti_forward",
                    )
                except Exception:
                    pass
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
        s = get_session()
        try:
            setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(message.chat.id)).first()
            if not setting:
                setting = ChatSetting(chat_id=str(message.chat.id), auto_remove_banned=value)
                s.add(setting)
            else:
                setting.auto_remove_banned = value
            s.commit()
            bot.reply_to(message, f"auto_remove_banned set to {value}")
        finally:
            s.close()


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
        s = get_session()
        try:
            setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(message.chat.id)).first()
            if not setting:
                setting = ChatSetting(chat_id=str(message.chat.id), anti_link=value)
                s.add(setting)
            else:
                setting.anti_link = value
            s.commit()
            bot.reply_to(message, f"anti_link set to {value}")
        finally:
            s.close()


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
        s = get_session()
        try:
            setting = s.query(ChatSetting).filter(ChatSetting.chat_id == str(message.chat.id)).first()
            if not setting:
                setting = ChatSetting(chat_id=str(message.chat.id), anti_forward=value)
                s.add(setting)
            else:
                setting.anti_forward = value
            s.commit()
            bot.reply_to(message, f"anti_forward set to {value}")
        finally:
            s.close()
        _save_settings(settings)
        bot.reply_to(message, f"anti_forward set to {value}")
