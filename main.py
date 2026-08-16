import os

from dotenv import load_dotenv
from telebot import TeleBot

from db import Base, engine
import models  # noqa: F401 — مدل‌ها باید قبل از create_all ایمپورت شوند
from groups.ban import ban_handler
from groups.unban import unban_handler
from groups.kick import kick_handler
from groups.mute import mute_handler
from groups.unmute import unmute_handler
from groups.warn import warn_handler
from groups.roles import roles_handler
from groups.messages import messages_handler
from groups.settings import settings_handler
from groups.logs import logs_handler
from groups.filter import filter_handler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN در فایل .env تنظیم نشده است.")

# ساخت جداول دیتابیس در صورت نبود
Base.metadata.create_all(bind=engine)

bot = TeleBot(BOT_TOKEN)

# ترتیب مهم است: telebot اولین هندلرِ منطبق را اجرا می‌کند و
# filter_handler یک هندلر catch-all ثبت می‌کند، پس باید آخر رجیستر شود
# تا دستورات هندلرهای دیگر را نبلعد.
HANDLERS = (
    ban_handler,
    unban_handler,
    kick_handler,
    mute_handler,
    unmute_handler,
    warn_handler,
    roles_handler,
    messages_handler,
    settings_handler,
    logs_handler,
    filter_handler,
)

for register in HANDLERS:
    register(bot)

bot.infinity_polling()
