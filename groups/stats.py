"""ماژول آمارگیری گروه — شمارش پیام‌ها و نمایش آمار جامع."""

from datetime import datetime, timedelta

import telebot
from telebot.apihelper import ApiTelegramException
from sqlalchemy import func, desc, extract

from utils.helpers import is_group, escape_html, build_user_mention
from utils.guards import command_guard
from groups.logs import log_action
from db import get_session
from models import MessageStat, Log, Warn, BannedWord, ContentRestriction

# ── ثابت‌ها ──────────────────────────────────────────
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

TRACKED_CONTENT_TYPES = [
    "text", "photo", "video", "sticker", "animation",
    "voice", "video_note", "document", "audio",
    "poll", "contact", "location",
]


def _now() -> datetime:
    return datetime.utcnow()


def _today_start() -> datetime:
    n = _now()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def _days_ago_start(days: int) -> datetime:
    return _today_start() - timedelta(days=days)


# ── شمارش پیام‌ها (قابل فراخوانی از ماژول‌های دیگر) ───
def track_message(message) -> None:
    """ثبت آمار یک پیام در دیتابیس.

    این تابع باید از هندلرهایی که پیام را پردازش می‌کنند
    فراخوانی شود (مثلاً filter.py یا restrict.py).
    خطاها بی‌صدا نادیده گرفته می‌شوند.
    """
    try:
        s = get_session()
        try:
            s.add(MessageStat(
                chat_id=str(message.chat.id),
                user_id=message.from_user.id,
                content_type=message.content_type,
                ts=_now(),
            ))
            s.commit()
        finally:
            s.close()
    except Exception:
        pass


# ── هندلرها ──────────────────────────────────────────
def stats_handler(bot: telebot.TeleBot):

    # ──────────────────────────────────────────────
    #  /stats — آمار کلی گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["stats"])
    def group_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        chat_id = str(message.chat.id)
        parts = message.text.split()
        period = "all"  # all | today | week | month
        if len(parts) >= 2 and parts[1].lower() in ("today", "week", "month"):
            period = parts[1].lower()

        s = get_session()
        try:
            # بازه زمانی
            if period == "today":
                since = _today_start()
                period_label = "امروز"
            elif period == "week":
                since = _days_ago_start(7)
                period_label = "۷ روز اخیر"
            elif period == "month":
                since = _days_ago_start(30)
                period_label = "۳۰ روز اخیر"
            else:
                since = None
                period_label = "کل دوره"

            # تعداد کل پیام‌ها
            q_total = s.query(func.count(MessageStat.id)).filter(
                MessageStat.chat_id == chat_id
            )
            if since:
                q_total = q_total.filter(MessageStat.ts >= since)
            total_msgs = q_total.scalar() or 0

            # تعداد کاربران فعال
            q_users = s.query(func.count(func.distinct(MessageStat.user_id))).filter(
                MessageStat.chat_id == chat_id
            )
            if since:
                q_users = q_users.filter(MessageStat.ts >= since)
            active_users = q_users.scalar() or 0

            # تعداد اکشن‌های مدیریتی
            q_mod = s.query(func.count(Log.id)).filter(Log.chat_id == chat_id)
            if since:
                q_mod = q_mod.filter(Log.ts >= since)
            mod_actions = q_mod.scalar() or 0

            # تعداد وارن‌های ثبت‌شده
            q_warns = s.query(func.count(Warn.id)).filter(Warn.chat_id == chat_id)
            if since:
                q_warns = q_warns.filter(Warn.ts >= since)
            total_warns = q_warns.scalar() or 0

            # تعداد کلمات فیلترشده
            banned_count = (
                s.query(func.count(BannedWord.id))
                .filter(BannedWord.chat_id == chat_id)
                .scalar() or 0
            )

            # تعداد قفل‌های محتوا
            restriction_count = (
                s.query(func.count(ContentRestriction.id))
                .filter(ContentRestriction.chat_id == chat_id)
                .scalar() or 0
            )

            text = (
                f"📊 <b>آمار گروه</b> ({period_label})\n"
                f"{'━' * 24}\n\n"
                f"💬 کل پیام‌ها: <b>{total_msgs:,}</b>\n"
                f"👥 کاربران فعال: <b>{active_users:,}</b>\n"
                f"⚠️ هشدارها: <b>{total_warns:,}</b>\n"
                f"🛡 اکشن‌های مدیریتی: <b>{mod_actions:,}</b>\n"
                f"🚫 کلمات فیلترشده: <b>{banned_count}</b>\n"
                f"🔒 قفل‌های محتوا: <b>{restriction_count}</b>\n"
            )

            bot.reply_to(message, text, parse_mode="HTML")

        finally:
            s.close()

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

        chat_id = str(message.chat.id)

        s = get_session()
        try:
            # تلاش برای گرفتن اطلاعات کاربر
            user_name = f"<code>{target_id}</code>"
            try:
                member = bot.get_chat_member(message.chat.id, target_id)
                user_name = build_user_mention(member.user)
            except ApiTelegramException:
                pass

            # کل پیام‌ها
            total = (
                s.query(func.count(MessageStat.id))
                .filter(MessageStat.chat_id == chat_id, MessageStat.user_id == target_id)
                .scalar() or 0
            )

            # پیام‌های امروز
            today_msgs = (
                s.query(func.count(MessageStat.id))
                .filter(
                    MessageStat.chat_id == chat_id,
                    MessageStat.user_id == target_id,
                    MessageStat.ts >= _today_start(),
                )
                .scalar() or 0
            )

            # پیام‌های ۷ روز اخیر
            week_msgs = (
                s.query(func.count(MessageStat.id))
                .filter(
                    MessageStat.chat_id == chat_id,
                    MessageStat.user_id == target_id,
                    MessageStat.ts >= _days_ago_start(7),
                )
                .scalar() or 0
            )

            # تفکیک نوع محتوا
            content_rows = (
                s.query(
                    MessageStat.content_type,
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id, MessageStat.user_id == target_id)
                .group_by(MessageStat.content_type)
                .order_by(desc("cnt"))
                .all()
            )

            # تعداد وارن‌ها
            warns = (
                s.query(func.count(Warn.id))
                .filter(Warn.chat_id == chat_id, Warn.user_id == target_id)
                .scalar() or 0
            )

            # فعال‌ترین ساعت
            hour_row = (
                s.query(
                    extract("hour", MessageStat.ts).label("h"),
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id, MessageStat.user_id == target_id)
                .group_by("h")
                .order_by(desc("cnt"))
                .first()
            )
            peak_hour = f"{int(hour_row[0]):02d}:00" if hour_row else "—"

            # فعال‌ترین روز هفته
            # SQLite: 0=یکشنبه, 1=دوشنبه, ..., 6=شنبه
            dow_names = ["یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"]
            dow_row = (
                s.query(
                    extract("dow", MessageStat.ts).label("d"),
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id, MessageStat.user_id == target_id)
                .group_by("d")
                .order_by(desc("cnt"))
                .first()
            )
            peak_day = dow_names[int(dow_row[0])] if dow_row else "—"

            # ساخت متن
            lines = [
                f"👤 <b>آمار کاربر</b>",
                f"کاربر: {user_name}",
                f"{'━' * 24}\n",
                f"💬 کل پیام‌ها: <b>{total:,}</b>",
                f"📅 امروز: <b>{today_msgs:,}</b>",
                f"📆 ۷ روز اخیر: <b>{week_msgs:,}</b>",
                f"⚠️ هشدارها: <b>{warns}</b>",
                f"🕐 فعال‌ترین ساعت: <b>{peak_hour}</b>",
                f"📆 فعال‌ترین روز: <b>{peak_day}</b>",
            ]

            if content_rows:
                lines.append("\n📊 تفکیک نوع محتوا:")
                for ctype, cnt in content_rows[:8]:
                    label = CONTENT_LABELS.get(ctype, ctype)
                    lines.append(f"  {label}: {cnt:,}")

            bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

        finally:
            s.close()

    # ──────────────────────────────────────────────
    #  /mystats — آمار خود کاربر (میانبر)
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["mystats"])
    def my_stats(message):
        if not is_group(message):
            return
        # فراخوانی userstats با ID خود کاربر
        message.text = f"/userstats {message.from_user.id}"
        user_stats(message)

    # ──────────────────────────────────────────────
    #  /top — فعال‌ترین اعضای گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["top"])
    def top_members(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        chat_id = str(message.chat.id)
        parts = message.text.split()
        period = "all"
        if len(parts) >= 2 and parts[1].lower() in ("today", "week", "month"):
            period = parts[1].lower()

        s = get_session()
        try:
            if period == "today":
                since = _today_start()
                period_label = "امروز"
            elif period == "week":
                since = _days_ago_start(7)
                period_label = "۷ روز اخیر"
            elif period == "month":
                since = _days_ago_start(30)
                period_label = "۳۰ روز اخیر"
            else:
                since = None
                period_label = "کل دوره"

            q = (
                s.query(
                    MessageStat.user_id,
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id)
            )
            if since:
                q = q.filter(MessageStat.ts >= since)
            rows = (
                q.group_by(MessageStat.user_id)
                .order_by(desc("cnt"))
                .limit(15)
                .all()
            )

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

        finally:
            s.close()

    # ──────────────────────────────────────────────
    #  /mediastats — تفکیک نوع محتوا در گروه
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["mediastats"])
    def media_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        chat_id = str(message.chat.id)
        parts = message.text.split()
        period = "all"
        if len(parts) >= 2 and parts[1].lower() in ("today", "week", "month"):
            period = parts[1].lower()

        s = get_session()
        try:
            if period == "today":
                since = _today_start()
                period_label = "امروز"
            elif period == "week":
                since = _days_ago_start(7)
                period_label = "۷ روز اخیر"
            elif period == "month":
                since = _days_ago_start(30)
                period_label = "۳۰ روز اخیر"
            else:
                since = None
                period_label = "کل دوره"

            q = (
                s.query(
                    MessageStat.content_type,
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id)
            )
            if since:
                q = q.filter(MessageStat.ts >= since)
            rows = (
                q.group_by(MessageStat.content_type)
                .order_by(desc("cnt"))
                .all()
            )

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

        finally:
            s.close()

    # ──────────────────────────────────────────────
    #  /hourly — فعالیت بر اساس ساعت روز
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["hourly"])
    def hourly_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        chat_id = str(message.chat.id)
        parts = message.text.split()
        period = "all"
        if len(parts) >= 2 and parts[1].lower() in ("today", "week", "month"):
            period = parts[1].lower()

        s = get_session()
        try:
            if period == "today":
                since = _today_start()
                period_label = "امروز"
            elif period == "week":
                since = _days_ago_start(7)
                period_label = "۷ روز اخیر"
            elif period == "month":
                since = _days_ago_start(30)
                period_label = "۳۰ روز اخیر"
            else:
                since = None
                period_label = "کل دوره"

            q = (
                s.query(
                    extract("hour", MessageStat.ts).label("h"),
                    func.count(MessageStat.id).label("cnt"),
                )
                .filter(MessageStat.chat_id == chat_id)
            )
            if since:
                q = q.filter(MessageStat.ts >= since)
            rows = q.group_by("h").order_by("h").all()

            if not rows:
                return bot.reply_to(message, "آماری ثبت نشده است.")

            hour_map = {int(h): c for h, c in rows}
            max_cnt = max(hour_map.values()) if hour_map else 1

            lines = [f"🕐 <b>فعالیت ساعتی گروه</b> ({period_label})\n"]
            for h in range(24):
                cnt = hour_map.get(h, 0)
                bar_len = int((cnt / max_cnt) * 15) if max_cnt > 0 else 0
                bar = "▓" * bar_len + "░" * (15 - bar_len)
                lines.append(f"  <code>{h:02d}:00</code> {bar} {cnt:,}")

            bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

        finally:
            s.close()

    # ──────────────────────────────────────────────
    #  /modstats — آمار اکشن‌های مدیریتی
    # ──────────────────────────────────────────────
    @bot.message_handler(commands=["modstats"])
    def mod_stats(message):
        err = command_guard(bot, message)
        if err:
            return bot.reply_to(message, err)

        chat_id = str(message.chat.id)
        parts = message.text.split()
        period = "all"
        if len(parts) >= 2 and parts[1].lower() in ("today", "week", "month"):
            period = parts[1].lower()

        s = get_session()
        try:
            if period == "today":
                since = _today_start()
                period_label = "امروز"
            elif period == "week":
                since = _days_ago_start(7)
                period_label = "۷ روز اخیر"
            elif period == "month":
                since = _days_ago_start(30)
                period_label = "۳۰ روز اخیر"
            else:
                since = None
                period_label = "کل دوره"

            q = (
                s.query(
                    Log.action,
                    func.count(Log.id).label("cnt"),
                )
                .filter(Log.chat_id == chat_id)
            )
            if since:
                q = q.filter(Log.ts >= since)
            rows = (
                q.group_by(Log.action)
                .order_by(desc("cnt"))
                .all()
            )

            if not rows:
                return bot.reply_to(message, "هیچ اکشن مدیریتی ثبت نشده.")

            action_labels = {
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

            total_mod = sum(cnt for _, cnt in rows)
            lines = [f"🛡 <b>آمار مدیریتی</b> ({period_label})\n"]
            for action, cnt in rows:
                label = action_labels.get(action, action)
                pct = (cnt / total_mod * 100) if total_mod > 0 else 0
                lines.append(f"  {label}: <b>{cnt:,}</b> ({pct:.1f}%)")

            lines.append(f"\n📈 جمع کل: <b>{total_mod:,}</b>")
            bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

        finally:
            s.close()

    # ──────────────────────────────────────────────
    #  /stats reset — پاکسازی آمار (فقط ادمین)
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

        s = get_session()
        try:
            if target == "messages" or target == "all":
                count = (
                    s.query(MessageStat)
                    .filter(MessageStat.chat_id == str(message.chat.id))
                    .delete()
                )
                s.commit()
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

        finally:
            s.close()
