"""بارگذاری تنظیمات برنامه از متغیرهای محیطی (.env)."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DB_PATH = DATA_DIR / "gapguard.db"

# قابل override از .env با DATABASE_URL (مثلاً برای postgres در پروداکشن)
DATABASE_URL = os.getenv("DATABASE_URL") or f"sqlite:///{DEFAULT_DB_PATH}"

BOT_TOKEN = os.getenv("BOT_TOKEN")


def get_bot_token() -> str:
    """توکن ربات را برمی‌گرداند و در صورت نبود، خطا می‌دهد."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN در فایل .env تنظیم نشده است.")
    return BOT_TOKEN
