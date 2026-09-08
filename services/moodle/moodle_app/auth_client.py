"""Поход в auth-service за токеном студента.

Токен живёт в памяти ровно на время обработки запроса: сохранять его здесь
нельзя — расшифровкой владеет только auth-service.
"""

import httpx
from sduhub_common.internal import INTERNAL_HEADER

TIMEOUT = httpx.Timeout(10.0)


class SessionInvalid(Exception):
    """Сессии нет, она протухла или токен больше не расшифровывается."""


class AuthUnavailable(Exception):
    """auth-service не ответил."""


class AuthClient:
    def __init__(self, base_url: str, internal_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {INTERNAL_HEADER: internal_key}

    async def token_for(self, session_id: str) -> tuple[str, str, int]:
        """Возвращает (token, student_id, moodle_userid) по идентификатору сессии."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{self._base}/internal/token/{session_id}", headers=self._headers
                )
        except httpx.HTTPError as exc:
            raise AuthUnavailable("auth-service недоступен") from exc

        if resp.status_code == 401:
            raise SessionInvalid("сессия недействительна")
        if resp.status_code != 200:
            raise AuthUnavailable(f"auth-service ответил {resp.status_code}")

        data = resp.json()
        return data["token"], data["student_id"], int(data["moodle_userid"])
