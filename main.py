import os
from dotenv import load_dotenv
from telebot import TeleBot

from groups.ban import ban_handler
from groups.unban import unban_handler
from groups.kick import kick_handler
from groups.mute import mute_handler
from groups.unmute import unmute_handler

# لود کردن فایل .env
load_dotenv()

# پاس دادن متغیر از فایل .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(BOT_TOKEN)

ban_handler(bot)
unban_handler(bot)
kick_handler(bot)
mute_handler(bot)
unmute_handler(bot)

bot.infinity_polling()
