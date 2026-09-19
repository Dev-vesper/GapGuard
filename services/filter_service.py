"""منطق فیلتر: کلمات ممنوعه، لینک و فوروارد."""

import re
from typing import List, Optional

from core.database import session_scope
from database import repositories as repo

LINK_PATTERN = re.compile(r"https?://|t\.me/|telegram\.me/")


def list_banned_words(chat_id) -> List[str]:
    with session_scope() as session:
        return repo.list_banned_words(session, chat_id)


def add_banned_word(chat_id, word: str) -> bool:
    """False اگر کلمه از قبل ثبت شده باشد."""
    with session_scope() as session:
        return repo.add_banned_word(session, chat_id, word)


def remove_banned_word(chat_id, word: str) -> None:
    with session_scope() as session:
        repo.remove_banned_word(session, chat_id, word)


def find_banned_word(text: str, words: List[str]) -> Optional[str]:
    """اولین کلمه ممنوعه‌ای که در متن پیدا شود."""
    for word in words:
        if word and re.search(r"\b" + re.escape(word) + r"\b", text):
            return word
    return None


def contains_link(text: str) -> bool:
    return bool(LINK_PATTERN.search(text))


def is_forwarded(message) -> bool:
    return getattr(message, "forward_from", None) is not None
