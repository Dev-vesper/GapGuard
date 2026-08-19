import os

from dotenv import load_dotenv
from telebot import TeleBot

from db import Base, engine
import models  # noqa: F401 — مدل‌ها باید قبل از create_all ایمپورت شوند
from groups.loader import register_all_handlers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در فایل .env تنظیم نشده است.")

# ساخت جداول دیتابیس در صورت نبود
Base.metadata.create_all(bind=engine)

bot = TeleBot(BOT_TOKEN)

# ثبت خودکار همه ماژول‌ها با اولویت‌بندی
register_all_handlers(bot)

bot.infinity_polling()
