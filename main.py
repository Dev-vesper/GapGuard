from telebot import TeleBot

from core.config import get_bot_token
from core.database import Base, engine
from core.logger import setup_logging
import models  # noqa: F401 — مدل‌ها باید قبل از create_all ایمپورت شوند
from groups.loader import register_all_handlers

setup_logging()

# ساخت جداول دیتابیس در صورت نبود
Base.metadata.create_all(bind=engine)

bot = TeleBot(get_bot_token())

# ثبت خودکار همه ماژول‌ها با اولویت‌بندی
register_all_handlers(bot)

bot.infinity_polling()
