"""Логи без секретов.

SECURITY.md: «токен всплывает в неожиданных местах — в логах локального сервера,
в скриншотах». Поэтому маскировать умеет сам логгер, а не каждый вызов вручную.
"""

import logging
import re

# Токен Moodle — 32 hex-символа. Ловим и его, и любые wstoken=/token= в URL.
_PATTERNS = [
    re.compile(r"(?i)\b(wstoken|token|privatetoken|password)=([^&\s\"']+)"),
    re.compile(r"\b[0-9a-f]{32}\b"),
]


def mask_secret(text: str) -> str:
    """Заменяет токены и пароли на ***. Применять к любой строке перед выводом."""
    masked = _PATTERNS[0].sub(r"\1=***", text)
    return _PATTERNS[1].sub("***", masked)


class _MaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_secret(record.msg)
        if record.args:
            record.args = tuple(
                mask_secret(a) if isinstance(a, str) else a for a in record.args
            )
        return True


def setup_logging(level: str = "INFO", service: str = "sduhub") -> logging.Logger:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    handler.addFilter(_MaskingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # uvicorn пишет пути запросов — там тоже может оказаться токен.
    # propagate=False обязателен: иначе запись уйдёт и в свой handler, и в корневой,
    # и каждая строка лога задвоится.
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False

    return logging.getLogger(service)
