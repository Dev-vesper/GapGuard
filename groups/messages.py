import telebot
from telebot.apihelper import ApiTelegramException

from utils.helpers import is_group, is_admin


def messages_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["delete"]) 
    def delete(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        if not message.reply_to_message:
            return bot.reply_to(message, "برای حذف پیام، به آن پیام ریپلای کنید.")

        try:
            bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "پیام حذف شد.")
        except ApiTelegramException as e:
            return bot.reply_to(message, f"خطا هنگام حذف پیام: {e}")


    @bot.message_handler(commands=["purge"]) 
    def purge(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")
        if not is_admin(bot, message.chat.id, message.from_user.id):
            return bot.reply_to(message, "فقط ادمین‌ها می‌توانند از این دستور استفاده کنند.")

        if not message.reply_to_message:
            return bot.reply_to(message, "برای پاکسازی محدوده، به اولین پیام ریپلای کنید.")

        start_id = message.reply_to_message.message_id
        end_id = message.message_id
        deleted = 0
        for mid in range(start_id, end_id + 1):
            try:
                bot.delete_message(message.chat.id, mid)
                deleted += 1
            except Exception:
                # ignore individual failures
                pass

        bot.reply_to(message, f"تلاش برای حذف پیام‌ها انجام شد. حذف شده: {deleted}")
