"""بارگذار خودکار ماژول‌های هندلر.

هر فایل در بسته groups/ که تابع <name>_handler(bot) صادر کند
به‌صورت خودکار کشف و ثبت می‌شود. ترتیب اجرا از طریق ماژول‌های
PRIORITY_MAP کنترل می‌شود (عدد کمتر = زودتر اجرا).

filter_handler باید آخر باشد چون یک catch-all handler ثبت می‌کند.
"""

import importlib
import pkgutil
from typing import Callable, List

import telebot


# ترتیب اجرا — عدد کمتر = اولویت بالاتر (زودتر اجرا)
PRIORITY_MAP = {
    "settings": 0,     # تنظیمات باید زودتر باشد چابق تنظیم گروه
    "logs": 10,
    "ban": 20,
    "unban": 21,
    "kick": 22,
    "mute": 23,
    "unmute": 24,
    "warn": 30,
    "roles": 40,
    "messages": 50,
    "restrict": 60,
    "stats": 70,       # آمارگیری — قبل از filter اجرا می‌شود
    "filter": 999,     # filter همیشه آخر — catch-all handler دارد
}

DEFAULT_PRIORITY = 100


def discover_handlers(package_name: str = "groups") -> List[Callable]:
    """هندلرهای قابل ثبت را از ماژول‌های بسته discovery می‌کند.

    هر ماژول باید تابعی با نام <name>_handler(bot) صادر کند.
    <name> از نام فایل مشتق می‌شود (مثلاً ban.py → ban_handler).

    Returns:
        لیست توابع هندلر مرتب‌شده بر اساس اولویت.
    """
    importlib.import_module(package_name)
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)

    found = []

    for importer, module_name, is_pkg in pkgutil.iter_modules(package_path):
        if module_name.startswith("_") or module_name in ("loader",):
            continue

        mod = importlib.import_module(f"{package_name}.{module_name}")

        # تابع <module_name>_handler را پیدا کن
        handler_fn_name = f"{module_name}_handler"
        handler_fn = getattr(mod, handler_fn_name, None)
        if handler_fn is None:
            continue

        priority = PRIORITY_MAP.get(module_name, DEFAULT_PRIORITY)
        found.append((priority, handler_fn, module_name))

    # مرتب‌سازی بر اساس اولویت
    found.sort(key=lambda x: x[0])

    print("📋 هندلرهای کشف‌شده:")
    for priority, fn, name in found:
        print(f"   [{priority:3d}] {name}_handler")

    return [fn for _, fn, _ in found]


def register_all_handlers(bot: telebot.TeleBot) -> None:
    """همه هندلرهای کشف‌شده را با bot ثبت می‌کند."""
    handlers = discover_handlers()
    for register in handlers:
        register(bot)
