"""بارگذار خودکار ماژول‌های هندلر.

هر فایل در بسته bot/handlers/ که تابع <name>_handler(bot) صادر کند
به‌صورت خودکار کشف و ثبت می‌شود. ترتیب اجرا از طریق PRIORITY_MAP
کنترل می‌شود (عدد کمتر = زودتر اجرا).

filter_handler باید آخر باشد چون یک catch-all handler ثبت می‌کند.
"""

import importlib
import pkgutil
from typing import Callable, List

import telebot

from core.logger import get_logger

logger = get_logger(__name__)

HANDLERS_PACKAGE = "bot.handlers"

# ترتیب اجرا — عدد کمتر = اولویت بالاتر (زودتر اجرا)
PRIORITY_MAP = {
    "settings": 0,     # تنظیمات باید زودتر باشد چابق تنظیم گروه
    "logs": 10,
    "moderation": 20,  # ban/unban/kick/mute/unmute/warn/unwarn/warns
    "roles": 40,
    "messages": 50,
    "restrict": 60,
    "stats": 70,       # آمارگیری — قبل از filter اجرا می‌شود
    "filter": 999,     # filter همیشه آخر — catch-all handler دارد
}

DEFAULT_PRIORITY = 100


def discover_handlers(package_name: str = HANDLERS_PACKAGE) -> List[Callable]:
    """هندلرهای قابل ثبت را از ماژول‌های بسته کشف می‌کند.

    هر ماژول باید تابعی با نام <name>_handler(bot) صادر کند.
    <name> از نام فایل مشتق می‌شود (مثلاً moderation.py → moderation_handler).

    Returns:
        لیست توابع هندلر مرتب‌شده بر اساس اولویت.
    """
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)

    found = []

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        if module_name.startswith("_"):
            continue

        mod = importlib.import_module(f"{package_name}.{module_name}")

        # تابع <module_name>_handler را پیدا کن
        handler_fn = getattr(mod, f"{module_name}_handler", None)
        if handler_fn is None:
            continue

        priority = PRIORITY_MAP.get(module_name, DEFAULT_PRIORITY)
        found.append((priority, handler_fn, module_name))

    # مرتب‌سازی بر اساس اولویت (پایدار — ترتیب الفبایی داخل هر اولویت حفظ می‌شود)
    found.sort(key=lambda x: x[0])

    logger.info("هندلرهای کشف‌شده: %s", ", ".join(name for _, _, name in found))

    return [fn for _, fn, _ in found]


def register_all_handlers(bot: telebot.TeleBot) -> None:
    """همه هندلرهای کشف‌شده را با bot ثبت می‌کند."""
    for register in discover_handlers():
        register(bot)
