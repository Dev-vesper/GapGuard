"""پیکربندی سیستم لاگینگ برنامه."""

import logging

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """لاگینگ ریشه را یک‌بار پیکربندی می‌کند."""
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
