import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, is_admin
from groups.logs import log_action


def messages_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["delete"]) 
    def delete(message):
        # اینا پروسس های الکی هست، بررسی هم نشن اتفاقی نمیفته فقط ادمین ها میتونن.
        # if not is_group(message):
        #     return
        # if not is_admin(bot, message.chat.id, message.from_user.id):
        #     return

        # if not message.reply_to_message:
        #     return bot.reply_to(message, "برای حذف پیام، به آن پیام ریپلای کنید.")

        try:
            bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "پیام حذف شد.")
            try:
                log_action(
                    action="delete_message",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    target_id=message.reply_to_message.from_user.id,
                    details=f"msg_id={message.reply_to_message.message_id}",
                )
            except Exception:
                pass
        except ApiTelegramException as e:
            return bot.reply_to(message, f"خطا هنگام حذف پیام: {e}")


    @bot.message_handler(commands=["purge"]) 
    def purge(message):
        # if not is_group(message):
        #     return
        # if not is_admin(bot, message.chat.id, message.from_user.id):
        #     return

        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return

        count = int(parts[1])
        if count <= 0:
            return
        
        start_id = message.message_id - count
        if start_id < 1:
            start_id = 1
            
        message_ids = list(range(start_id, message.message_id))
        deleted_count = 0

        for msg_id in message_ids:
            try:
                bot.delete_message(message.chat.id, msg_id)
                deleted_count += 1
            except Exception:
                pass

        if deleted_count > 0:
            bot.send_message(
                message.chat.id, 
                f"✅ پاکسازی انجام شد.\nتعداد پیام‌های حذف شده: {deleted_count}"
            )
            
            try:
                log_action(
                    action="purge",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    details=f"count={deleted_count}",
                )
            except Exception:
                pass
        else:
            bot.send_message(message.chat.id, "❌ عملیات با شکست مواجه شد.")
