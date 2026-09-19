"""دستورات آمارگیری گروه."""

import telebot
from telebot.apihelper import ApiTelegramException

from bot.guards import command_guard
from bot.helpers import build_user_mention, is_group
from services import stats_service
from services.log_service import log_action

CONTENT_LABELS = {
    "text": "📝 متن",
    "photo": "🖼 عکس",
    "video": "🎬 ویدیو",
    "sticker": "😄 استیکر",
    "animation": "🎞 گیف",
    "voice": "🎤 ویس",
    "video_note": "🔘 ویدیو نوت",
    "document": "📄 فایل",
    "audio": "🎵 آدیو",
    "poll": "📊 نظرسنجی",
    "contact": "📱 کانتکت",
    "location": "📍 لوکیشن",
}

# SQLite: 0=یکشنبه, 1=دوشنبه, ..., 6=شنبه
DOW_NAMES = ["یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"]

ACTION_LABELS = {
    "ban": "🚫 بن",
    "unban": "✅ آنبن",
    "kick": "👢 کیک",
    "mute": "🔇 میوت",
    "unmute": "🔊 آنمیوت",
    "warn": "⚠️ وارن",
    "auto_kick_on_max_warn": "⚡ حذف خودکار",
    "delete_message": "🗑 حذف پیام",
    "purge": "🧹 پاکسازی",
    "auto_delete": "🗑 حذف خودکار (فیلتر)",
    "auto_delete_content_restriction": "🔒 حذف خودکار (قفل محتوا)",
    "promote": "⬆️ ارتقا",
    "restrict_content_add": "🔒 اضافه کردن قفل",
    "restrict_content_remove": "🔓 حذف قفل",
    "restrict_user_content_add": "🔒 قفل شخصی",
    "restrict_user_content_remove": "🔓 حذف قفل شخصی",
}


def _send_user_stats(bot: telebot.TeleBot, message, target_id: int) -> None:
    """قالب‌بندی و ارسال آمار یک کاربر — مشترک بین /userstats و /mystats."""
    try:
        member = bot.get_chat_member(message.chat.id, target_id)
        user_name = build_user_mention(member.user)
    except ApiTelegramException:
        user_name = f"<code>{target_id}</code>"

    data = stats_service.user_stats(message.chat.id, target_id)

    peak_hour = f"{data.peak_hour:02d}:00" if data.peak_hour is not None else "—"
    peak_day = DOW_NAMES[data.peak_day] if data.peak_day is not None else "—"

    lines = [
        "👤 <b>آمار کاربر</b>",
        f"کاربر: {user_name}",
        f"{'━' * 24}\n",
        f"💬 کل پیام‌ها: <b>{data.total:,}</b>",
        f"📅 امروز: <b>{data.today:,}</b>",
        f"📆 ۷ روز اخیر: <b>{data.week:,}</b>",
        f"⚠️ هشدارها: <b>{data.warns}</b>",
        f"🕐 فعال‌ترین ساعت: <b>{peak_hour}</b>",
        f"📆 فعال‌ترین روز: <b>{peak_day}</b>",
    ]

    if data.content:
        lines.append("\n📊 تفکیک نوع محتوا:")
        for ctype, cnt in data.content[:8]:
            label = CONTENT_LABELS.get(ctype, ctype)
            lines.append(f"  {label}: {cnt:,}")

    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")


def stats_handler(bot: telebot.TeleBot):

    # ──────────────────────────────────────────────
    #  /stats — آمار کلی گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["stats"])
    def group_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        since, period_label = stats_service.resolve_period(message.text.split())
        data = stats_service.group_stats(message.chat.id, since, period_label)

        text = (
            f"📊 <b>آمار گروه</b> ({period_label})\n"
            f"{'━' * 24}\n\n"
            f"💬 کل پیام‌ها: <b>{data.total_messages:,}</b>\n"
            f"👥 کاربران فعال: <b>{data.active_users:,}</b>\n"
            f"⚠️ هشدارها: <b>{data.total_warns:,}</b>\n"
            f"🛡 اکشن‌های مدیریتی: <b>{data.mod_actions:,}</b>\n"
            f"🚫 کلمات فیلترشده: <b>{data.banned_words}</b>\n"
            f"🔒 قفل‌های محتوا: <b>{data.content_locks}</b>\n"
        )

        bot.reply_to(message, text, parse_mode="HTML")

    # ──────────────────────────────────────────────
    #  /userstats — آمار یک کاربر خاص
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["userstats"])
    def user_stats(message):
        if not is_group(message):
            return bot.reply_to(message, "این دستور فقط در گروه قابل استفاده است.")

        # تشخیص کاربر هدف
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
        else:
            parts = message.text.split()
            if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
                target_id = int(parts[1])

        if not target_id:
            target_id = message.from_user.id

        _send_user_stats(bot, message, target_id)

    # ──────────────────────────────────────────────
    #  /mystats — آمار خود کاربر (میانبر)
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["mystats"])
    def my_stats(message):
        if not is_group(message):
            return

        _send_user_stats(bot, message, message.from_user.id)

    # ──────────────────────────────────────────────
    #  /top — فعال‌ترین اعضای گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["top"])
    def top_members(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        since, period_label = stats_service.resolve_period(message.text.split())
        rows = stats_service.top_members(message.chat.id, since)

        if not rows:
            return bot.reply_to(message, "آماری ثبت نشده است.")

        medals = ["🥇", "🥈", "🥉"]
        lines = [f"🏆 <b>فعال‌ترین اعضای گروه</b> ({period_label})\n"]
        for i, (uid, cnt) in enumerate(rows):
            medal = medals[i] if i < 3 else f" {i+1}."
            try:
                member = bot.get_chat_member(message.chat.id, uid)
                name = build_user_mention(member.user)
            except ApiTelegramException:
                name = f"<code>{uid}</code>"
            lines.append(f"{medal} {name} — <b>{cnt:,}</b> پیام")

        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

    # ──────────────────────────────────────────────
    #  /mediastats — تفکیک نوع محتوا در گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["mediastats"])
    def media_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        since, period_label = stats_service.resolve_period(message.text.split())
        rows = stats_service.content_stats(message.chat.id, since)

        if not rows:
            return bot.reply_to(message, "آماری ثبت نشده است.")

        total = sum(cnt for _, cnt in rows)
        lines = [f"📊 <b>تفکیک نوع محتوا</b> ({period_label})\n"]
        for ctype, cnt in rows:
            label = CONTENT_LABELS.get(ctype, ctype)
            pct = (cnt / total * 100) if total > 0 else 0
            bar_len = int(pct / 5)  # هر بلوک = ۵٪
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"{label}\n  <code>{bar}</code> {cnt:,} ({pct:.1f}%)")

        lines.append(f"\n📈 جمع کل: <b>{total:,}</b>")
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

    # ──────────────────────────────────────────────
    #  /hourly — فعالیت بر اساس ساعت روز
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["hourly"])
    def hourly_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        since, period_label = stats_service.resolve_period(message.text.split())
        hour_map = stats_service.hourly_stats(message.chat.id, since)

        if not hour_map:
            return bot.reply_to(message, "آماری ثبت نشده است.")

        max_cnt = max(hour_map.values()) if hour_map else 1

        lines = [f"🕐 <b>فعالیت ساعتی گروه</b> ({period_label})\n"]
        for h in range(24):
            cnt = hour_map.get(h, 0)
            bar_len = int((cnt / max_cnt) * 15) if max_cnt > 0 else 0
            bar = "▓" * bar_len + "░" * (15 - bar_len)
            lines.append(f"  <code>{h:02d}:00</code> {bar} {cnt:,}")

        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

    # ──────────────────────────────────────────────
    #  /modstats — آمار اکشن‌های مدیریتی
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["modstats"])
    def mod_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        since, period_label = stats_service.resolve_period(message.text.split())
        rows = stats_service.moderation_stats(message.chat.id, since)

        if not rows:
            return bot.reply_to(message, "هیچ اکشن مدیریتی ثبت نشده.")

        total_mod = sum(cnt for _, cnt in rows)
        lines = [f"🛡 <b>آمار مدیریتی</b> ({period_label})\n"]
        for action, cnt in rows:
            label = ACTION_LABELS.get(action, action)
            pct = (cnt / total_mod * 100) if total_mod > 0 else 0
            lines.append(f"  {label}: <b>{cnt:,}</b> ({pct:.1f}%)")

        lines.append(f"\n📈 جمع کل: <b>{total_mod:,}</b>")
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

    # ──────────────────────────────────────────────
    #  /stats_reset — پاکسازی آمار (فقط ادمین)
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["stats_reset"])
    def stats_reset(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        parts = message.text.split()
        target = "messages"  # messages | all
        if len(parts) >= 2:
            target = parts[1].lower()

        if target == "messages" or target == "all":
            count = stats_service.reset_message_stats(message.chat.id)
            bot.reply_to(
                message,
                f"✅ <b>{count:,}</b> رکورد پیام پاکسازی شد.",
                parse_mode="HTML",
            )
            log_action(
                action="stats_reset",
                chat_id=message.chat.id,
                admin_id=message.from_user.id,
                details=f"target={target}, count={count}",
            )
        else:
            bot.reply_to(message, "پارامتر نامعتبر. استفاده: /stats_reset messages|all")
