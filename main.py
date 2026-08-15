from telebot import TeleBot

from groups.ban import ban_handler
from groups.unban import unban_handler
from groups.kick import kick_handler
from groups.mute import mute_handler

bot = TeleBot("BOT_TOKEN")

ban_handler(bot)
unban_handler(bot)
kick_handler(bot)
mute_handler(bot)

bot.infinity_polling()