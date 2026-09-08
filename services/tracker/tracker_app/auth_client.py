"""Кто стоит за сессией. Токен Moodle трекеру не нужен и не запрашивается."""

from uuid import UUID

import httpx

from sduhub_common.internal import INTERNAL_HEADER

TIMEOUT = httpx.Timeout(10.0)


class SessionInvalid(Exception):
    pass


class AuthUnavailable(Exception):
    pass


class AuthClient:
    def __init__(self, base_url: str, internal_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {INTERNAL_HEADER: internal_key}

    async def student_id(self, session_id: str) -> UUID:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{self._base}/internal/session/{session_id}", headers=self._headers
                )
        except httpx.HTTPError as exc:
            raise AuthUnavailable("auth-service недоступен") from exc

        if resp.status_code == 401:
            raise SessionInvalid("сессия недействительна")
        if resp.status_code != 200:
            raise AuthUnavailable(f"auth-service ответил {resp.status_code}")

        return UUID(resp.json()["student_id"])
