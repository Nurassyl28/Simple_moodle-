"""Подписанные ссылки на файлы Moodle.

SECURITY.md запрещает отдавать во фронтенд ссылки с токеном. Поэтому наружу уходит
подписанная ссылка вида `?ref=<base64(url)>.<подпись>`: браузер видит только её,
а токен подставляет moodle-service у себя.

Подпись привязана к студенту — чужую ссылку подставить не получится, и она
протухает, чтобы утёкшая из истории браузера ссылка не работала вечно.
"""

import base64
import hmac
import time
from hashlib import sha256

SEPARATOR = "."
DEFAULT_TTL = 3600  # час: ссылка нужна ровно на время клика


class FileRefError(ValueError):
    """Ссылка подделана, испорчена или протухла."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(key: str, payload: str) -> str:
    return _b64e(hmac.new(key.encode(), payload.encode(), sha256).digest())


def make_ref(key: str, student_id: str, file_url: str, ttl: int = DEFAULT_TTL) -> str:
    """Собирает ссылку, которую не стыдно отдать в браузер."""
    expires = int(time.time()) + ttl
    payload = f"{_b64e(file_url.encode())}{SEPARATOR}{student_id}{SEPARATOR}{expires}"
    return f"{payload}{SEPARATOR}{_sign(key, payload)}"


def read_ref(key: str, student_id: str, ref: str) -> str:
    """Проверяет подпись, срок и владельца. Возвращает исходный URL файла."""
    try:
        url_part, ref_student, expires_part, signature = ref.split(SEPARATOR)
    except ValueError as exc:
        raise FileRefError("ссылка испорчена") from exc

    payload = f"{url_part}{SEPARATOR}{ref_student}{SEPARATOR}{expires_part}"
    if not hmac.compare_digest(signature, _sign(key, payload)):
        raise FileRefError("подпись не сходится")

    # Владельца сверяем после подписи: до неё содержимому вообще нельзя верить.
    if not hmac.compare_digest(ref_student, student_id):
        raise FileRefError("ссылка выдана другому студенту")

    if int(expires_part) < time.time():
        raise FileRefError("ссылка устарела")

    try:
        return _b64d(url_part).decode()
    except Exception as exc:
        raise FileRefError("ссылка испорчена") from exc
