import telebot
from telebot.apihelper import ApiTelegramException

from utils.guards import command_guard
from groups.logs import log_action


def messages_handler(bot: telebot.TeleBot):

    @bot.message_handler(commands=["delete"])
    def delete(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        if not message.reply_to_message:
            return bot.reply_to(message, "برای حذف پیام، به آن پیام ریپلای کنید.")

        target_msg = message.reply_to_message
        try:
            bot.delete_message(message.chat.id, target_msg.message_id)
        except ApiTelegramException as e:
            return bot.reply_to(message, f"خطا هنگام حذف پیام: {e}")

        bot.reply_to(message, "پیام حذف شد.")
        log_action(
            action="delete_message",
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            target_id=target_msg.from_user.id if target_msg.from_user else None,
            details=f"msg_id={target_msg.message_id}",
        )

    @bot.message_handler(commands=["purge"])
    def purge(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            return bot.reply_to(message, "استفاده: /purge <تعداد>")

        count = int(parts[1])
        if count <= 0:
            return bot.reply_to(message, "تعداد باید 1 یا بیشتر باشد.")

        start_id = max(1, message.message_id - count)
        deleted_count = 0

        for msg_id in range(start_id, message.message_id):
            try:
                bot.delete_message(message.chat.id, msg_id)
                deleted_count += 1
            except Exception:
                pass

        if deleted_count > 0:
            bot.send_message(
                message.chat.id,
                f"✅ پاکسازی انجام شد.\nتعداد پیام‌های حذف شده: {deleted_count}",
            )
            log_action(
                action="purge",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                details=f"count={deleted_count}",
            )
        else:
            bot.send_message(message.chat.id, "❌ عملیات با شکست مواجه شد.")
