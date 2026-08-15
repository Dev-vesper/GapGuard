from telebot import TeleBot

from groups.ban import ban_handler
from groups.unban import unban_handler


bot = TeleBot("TOKEN")

ban_handler(bot)
unban_handler(bot)

bot.infinity_polling()