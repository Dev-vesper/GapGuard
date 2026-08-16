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
        
        # بعلاوه ۱ رو حذف کردم تا واقعا اون تعداد پیامی که وارد شده حذف بشه
        start_id = message.message_id - count
        if start_id < 1:
            start_id = 1
            
        message_ids = list(range(start_id, message.message_id + 1))

        try:
            batch_size = 100
            for i in range(0, len(message_ids), batch_size):
                batch = message_ids[i:i + batch_size]
                bot.delete_messages(message.chat.id, batch) # api رسمی تلگرام برا حذف پیام
            
            bot.send_message(
                message.chat.id, 
                f"✅ پاکسازی انجام شد.\nتعداد پیام‌های حذف شده: {len(message_ids)}"
            )
            
            try:
                log_action(
                    action="purge",
                    chat_id=message.chat.id,
                    admin_id=message.from_user.id,
                    details=f"count={len(message_ids)}",
                )
            except Exception:
                pass

        except Exception:
            bot.send_message(message.chat.id, "❌ عملیات با شکست مواجه شد.")
