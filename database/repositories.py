"""لایه دسترسی به داده — تمام کوئری‌های CRUD اینجا متمرکز است.

توابع این ماژول سشن نمی‌سازند و تصمیمی نمی‌گیرند؛ سشن از بیرون تزریق
می‌شود تا مرز تراکنش در اختیار لایه سرویس بماند.
"""

from typing import Dict, List, Optional

from sqlalchemy import desc, extract, func
from sqlalchemy.orm import Session

from database.models import (
    BannedWord,
    ChatSetting,
    ContentRestriction,
    Log,
    MessageStat,
    SpecialMember,
    Tag,
    Warn,
)


def _chat(chat_id) -> str:
    """chat_id همیشه به‌صورت رشته ذخیره می‌شود (اعداد منفی بزرگ تلگرام)."""
    return str(chat_id)


def _scope_to_user(query, column, user_id: Optional[int]):
    """دامنه را به یک کاربر خاص یا به «کل گروه» (user_id تهی) محدود می‌کند."""
    if user_id is not None:
        return query.filter(column == user_id)
    return query.filter(column.is_(None))


# ── تنظیمات گروه ─────────────────────────────────────
def get_setting(session: Session, chat_id) -> Optional[ChatSetting]:
    return (
        session.query(ChatSetting)
        .filter(ChatSetting.chat_id == _chat(chat_id))
        .first()
    )


def upsert_setting(session: Session, chat_id, **fields) -> None:
    setting = get_setting(session, chat_id)
    if not setting:
        setting = ChatSetting(chat_id=_chat(chat_id))
        session.add(setting)
    for name, value in fields.items():
        setattr(setting, name, value)


# ── وارن‌ها ──────────────────────────────────────────
def add_warn(session: Session, chat_id, user_id: int, reason: Optional[str]) -> None:
    session.add(Warn(chat_id=_chat(chat_id), user_id=user_id, reason=reason))


def count_warns(
    session: Session, chat_id, user_id: Optional[int] = None, since=None
) -> int:
    query = session.query(Warn).filter(Warn.chat_id == _chat(chat_id))
    if user_id is not None:
        query = query.filter(Warn.user_id == user_id)
    if since:
        query = query.filter(Warn.ts >= since)
    return query.count()


def list_warns(session: Session, chat_id, user_id: int) -> List[Warn]:
    return (
        session.query(Warn)
        .filter(Warn.chat_id == _chat(chat_id), Warn.user_id == user_id)
        .order_by(Warn.ts)
        .all()
    )


def last_warn(session: Session, chat_id, user_id: int) -> Optional[Warn]:
    return (
        session.query(Warn)
        .filter(Warn.chat_id == _chat(chat_id), Warn.user_id == user_id)
        .order_by(Warn.ts.desc())
        .first()
    )


def delete_warn(session: Session, warn: Warn) -> None:
    session.delete(warn)


def delete_user_warns(session: Session, chat_id, user_id: int) -> int:
    return (
        session.query(Warn)
        .filter(Warn.chat_id == _chat(chat_id), Warn.user_id == user_id)
        .delete()
    )


def top_warned(session: Session, chat_id, limit: int = 20):
    return (
        session.query(Warn.user_id, func.count(Warn.id).label("cnt"))
        .filter(Warn.chat_id == _chat(chat_id))
        .group_by(Warn.user_id)
        .order_by(desc("cnt"))
        .limit(limit)
        .all()
    )


# ── کلمات فیلترشده ──────────────────────────────────
def list_banned_words(session: Session, chat_id) -> List[str]:
    rows = (
        session.query(BannedWord)
        .filter(BannedWord.chat_id == _chat(chat_id))
        .all()
    )
    return [row.word for row in rows]


def add_banned_word(session: Session, chat_id, word: str) -> bool:
    """False اگر کلمه از قبل ثبت شده باشد."""
    exists = (
        session.query(BannedWord)
        .filter(BannedWord.chat_id == _chat(chat_id), BannedWord.word == word)
        .first()
    )
    if exists:
        return False
    session.add(BannedWord(chat_id=_chat(chat_id), word=word))
    return True


def remove_banned_word(session: Session, chat_id, word: str) -> None:
    session.query(BannedWord).filter(
        BannedWord.chat_id == _chat(chat_id), BannedWord.word == word
    ).delete()


# ── لاگ‌ها ───────────────────────────────────────────
def insert_log(
    session: Session,
    action: str,
    chat_id,
    admin_id: Optional[int] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    session.add(
        Log(
            action=action,
            chat_id=_chat(chat_id),
            admin_id=admin_id,
            target_id=target_id,
            details=details,
        )
    )


def list_logs(
    session: Session, action: Optional[str] = None, page: int = 1, per_page: int = 10
) -> List[Log]:
    query = session.query(Log)
    if action:
        query = query.filter(Log.action == action)
    return (
        query.order_by(desc(Log.ts))
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def count_logs(session: Session, chat_id, since=None) -> int:
    query = session.query(func.count(Log.id)).filter(Log.chat_id == _chat(chat_id))
    if since:
        query = query.filter(Log.ts >= since)
    return query.scalar() or 0


def action_breakdown(session: Session, chat_id, since=None):
    query = session.query(Log.action, func.count(Log.id).label("cnt")).filter(
        Log.chat_id == _chat(chat_id)
    )
    if since:
        query = query.filter(Log.ts >= since)
    return query.group_by(Log.action).order_by(desc("cnt")).all()


# ── قفل محتوا ────────────────────────────────────────
def list_restrictions(
    session: Session, chat_id, user_id: Optional[int] = None
) -> List[str]:
    query = session.query(ContentRestriction).filter(
        ContentRestriction.chat_id == _chat(chat_id)
    )
    query = _scope_to_user(query, ContentRestriction.user_id, user_id)
    return [row.content_type for row in query.all()]


def add_restriction(
    session: Session, chat_id, content_type: str, user_id: Optional[int] = None
) -> bool:
    """False اگر این قفل از قبل وجود داشته باشد."""
    query = session.query(ContentRestriction).filter(
        ContentRestriction.chat_id == _chat(chat_id),
        ContentRestriction.content_type == content_type,
    )
    query = _scope_to_user(query, ContentRestriction.user_id, user_id)
    if query.first():
        return False
    session.add(
        ContentRestriction(
            chat_id=_chat(chat_id), user_id=user_id, content_type=content_type
        )
    )
    return True


def remove_restriction(
    session: Session, chat_id, content_type: str, user_id: Optional[int] = None
) -> bool:
    """False اگر این قفل وجود نداشته باشد."""
    query = session.query(ContentRestriction).filter(
        ContentRestriction.chat_id == _chat(chat_id),
        ContentRestriction.content_type == content_type,
    )
    query = _scope_to_user(query, ContentRestriction.user_id, user_id)
    return query.delete() > 0


def count_restrictions(session: Session, chat_id) -> int:
    return (
        session.query(func.count(ContentRestriction.id))
        .filter(ContentRestriction.chat_id == _chat(chat_id))
        .scalar()
        or 0
    )


# ── آمار پیام‌ها ─────────────────────────────────────
def add_message_stat(session: Session, chat_id, user_id: int, content_type: str, ts) -> None:
    session.add(
        MessageStat(
            chat_id=_chat(chat_id),
            user_id=user_id,
            content_type=content_type,
            ts=ts,
        )
    )


def count_messages(
    session: Session, chat_id, user_id: Optional[int] = None, since=None
) -> int:
    query = session.query(func.count(MessageStat.id)).filter(
        MessageStat.chat_id == _chat(chat_id)
    )
    if user_id is not None:
        query = query.filter(MessageStat.user_id == user_id)
    if since:
        query = query.filter(MessageStat.ts >= since)
    return query.scalar() or 0


def count_active_users(session: Session, chat_id, since=None) -> int:
    query = session.query(func.count(func.distinct(MessageStat.user_id))).filter(
        MessageStat.chat_id == _chat(chat_id)
    )
    if since:
        query = query.filter(MessageStat.ts >= since)
    return query.scalar() or 0


def content_breakdown(
    session: Session, chat_id, user_id: Optional[int] = None, since=None
):
    query = session.query(
        MessageStat.content_type, func.count(MessageStat.id).label("cnt")
    ).filter(MessageStat.chat_id == _chat(chat_id))
    if user_id is not None:
        query = query.filter(MessageStat.user_id == user_id)
    if since:
        query = query.filter(MessageStat.ts >= since)
    return query.group_by(MessageStat.content_type).order_by(desc("cnt")).all()


def time_breakdown(
    session: Session,
    chat_id,
    field: str,
    user_id: Optional[int] = None,
    since=None,
    order_by_count: bool = True,
):
    """تجمیع بر اساس بخشی از زمان (`hour` یا `dow`).

    order_by_count=True برای «فعال‌ترین ساعت/روز» و False برای نمودار ساعتی.
    """
    query = session.query(
        extract(field, MessageStat.ts).label("bucket"),
        func.count(MessageStat.id).label("cnt"),
    ).filter(MessageStat.chat_id == _chat(chat_id))
    if user_id is not None:
        query = query.filter(MessageStat.user_id == user_id)
    if since:
        query = query.filter(MessageStat.ts >= since)
    query = query.group_by("bucket")
    query = query.order_by(desc("cnt")) if order_by_count else query.order_by("bucket")
    return query.all()


def top_members(session: Session, chat_id, since=None, limit: int = 15):
    query = session.query(
        MessageStat.user_id, func.count(MessageStat.id).label("cnt")
    ).filter(MessageStat.chat_id == _chat(chat_id))
    if since:
        query = query.filter(MessageStat.ts >= since)
    return (
        query.group_by(MessageStat.user_id)
        .order_by(desc("cnt"))
        .limit(limit)
        .all()
    )


def count_banned_words(session: Session, chat_id) -> int:
    return (
        session.query(func.count(BannedWord.id))
        .filter(BannedWord.chat_id == _chat(chat_id))
        .scalar()
        or 0
    )


def reset_message_stats(session: Session, chat_id) -> int:
    return (
        session.query(MessageStat)
        .filter(MessageStat.chat_id == _chat(chat_id))
        .delete()
    )


# ── نقش‌ها (ممبر ویژه و تگ) ──────────────────────────
def list_special_members(session: Session, chat_id) -> List[int]:
    return [
        row.user_id
        for row in session.query(SpecialMember)
        .filter(SpecialMember.chat_id == _chat(chat_id))
        .all()
    ]


def add_special_member(session: Session, chat_id, user_id: int) -> None:
    session.add(SpecialMember(chat_id=_chat(chat_id), user_id=user_id))


def remove_special_member(session: Session, chat_id, user_id: int) -> None:
    session.query(SpecialMember).filter(
        SpecialMember.chat_id == _chat(chat_id), SpecialMember.user_id == user_id
    ).delete()


def list_tags(session: Session, chat_id) -> Dict[str, str]:
    return {
        str(row.user_id): row.tag
        for row in session.query(Tag).filter(Tag.chat_id == _chat(chat_id)).all()
    }


def set_tag(session: Session, chat_id, user_id: int, tag_text: str) -> None:
    tag = (
        session.query(Tag)
        .filter(Tag.chat_id == _chat(chat_id), Tag.user_id == user_id)
        .first()
    )
    if not tag:
        session.add(Tag(chat_id=_chat(chat_id), user_id=user_id, tag=tag_text))
    else:
        tag.tag = tag_text


def remove_tag(session: Session, chat_id, user_id: int) -> None:
    session.query(Tag).filter(
        Tag.chat_id == _chat(chat_id), Tag.user_id == user_id
    ).delete()
