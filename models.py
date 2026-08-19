from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from db import Base


class ChatSetting(Base):
    __tablename__ = "chat_settings"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True, nullable=False)
    max_warns = Column(Integer, default=3)
    auto_remove_banned = Column(Boolean, default=True)
    anti_link = Column(Boolean, default=False)
    anti_forward = Column(Boolean, default=False)


class Warn(Base):
    __tablename__ = "warns"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    reason = Column(Text)
    ts = Column(DateTime, default=datetime.utcnow)


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    action = Column(String, index=True)
    chat_id = Column(String, index=True)
    admin_id = Column(Integer, index=True, nullable=True)
    target_id = Column(Integer, index=True, nullable=True)
    details = Column(Text)


class SpecialMember(Base):
    __tablename__ = "special_members"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True)
    user_id = Column(Integer, index=True)


class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True)
    user_id = Column(Integer, index=True)
    tag = Column(Text)


class BannedWord(Base):
    __tablename__ = "banned_words"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True)
    word = Column(String, index=True)


class ContentRestriction(Base):
    """قفل انواع محتوا در گروه یا برای یک کاربر خاص."""
    __tablename__ = "content_restrictions"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=True)  # None = اعمال روی کل گروه
    content_type = Column(String, index=True, nullable=False)  # photo, video, sticker, ...
    ts = Column(DateTime, default=datetime.utcnow)


class MessageStat(Base):
    """شمارش پیام‌ها برای آمارگیری گروه."""
    __tablename__ = "message_stats"
    id = Column(Integer, primary_key=True)
    chat_id = Column(String, index=True, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    content_type = Column(String, index=True, nullable=False)  # text, photo, sticker, ...
    ts = Column(DateTime, default=datetime.utcnow, index=True)
