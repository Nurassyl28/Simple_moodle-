"""Клиент Moodle Web Services.

Все вызовы идут через один callMoodle: Moodle отвечает кодом 200 даже на ошибку,
а настоящая ошибка лежит в поле `exception` — проверять её нужно всегда, поэтому
проверка живёт здесь, а не в каждом обработчике (docs/moodle-api-notes.md).
"""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

REST_PATH = "/webservice/rest/server.php"
TIMEOUT = httpx.Timeout(20.0)


class MoodleError(Exception):
    """Moodle вернул exception. errorcode — машинный код причины."""

    def __init__(self, errorcode: str, message: str = "") -> None:
        super().__init__(errorcode)
        self.errorcode = errorcode
        self.message = message


class MoodleUnavailable(Exception):
    """Moodle не ответил или ответил не-JSON."""


class InvalidToken(MoodleError):
    """Токен сброшен или отозван — студенту нужен повторный вход."""


class ExternalFileRefused(Exception):
    """Ссылка ведёт не в Moodle. Токен туда отправлять нельзя."""


class MoodleClient:
    def __init__(self, site: str, token: str) -> None:
        self._site = site.rstrip("/")
        self._token = token

    async def call(self, function: str, **params: Any) -> Any:
        query = {
            "wstoken": self._token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
            **{k: v for k, v in params.items() if v is not None},
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(f"{self._site}{REST_PATH}", params=query)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            # В тексте httpx-ошибки лежит URL с токеном — наружу его не пускаем.
            raise MoodleUnavailable(f"Moodle не ответил на {function}") from exc
        except ValueError as exc:
            raise MoodleUnavailable(f"Moodle вернул не JSON на {function}") from exc

        if isinstance(data, dict) and "exception" in data:
            code = data.get("errorcode", "unknown")
            if code == "invalidtoken":
                raise InvalidToken(code, data.get("message", ""))
            raise MoodleError(code, data.get("message", ""))

        return data

    # --- проверенные функции (docs/moodle-api-notes.md) ---

    async def site_info(self) -> dict:
        return await self.call("core_webservice_get_site_info")

    async def courses(self, userid: int) -> list[dict]:
        return await self.call("core_enrol_get_users_courses", userid=userid)

    async def grade_items(self, courseid: int, userid: int) -> dict:
        return await self.call(
            "gradereport_user_get_grade_items", courseid=courseid, userid=userid
        )

    async def course_contents(self, courseid: int) -> list[dict]:
        return await self.call("core_course_get_contents", courseid=courseid)

    async def upcoming_events(self, timesortfrom: int | None = None) -> dict:
        if timesortfrom is None:
            timesortfrom = int(datetime.now(UTC).timestamp())
        return await self.call(
            "core_calendar_get_action_events_by_timesort", timesortfrom=timesortfrom
        )

    def is_moodle_url(self, url: str) -> bool:
        """Тот ли это хост, которому вообще можно показывать токен."""
        return urlparse(url).netloc.lower() == urlparse(self._site).netloc.lower()

    async def download(self, file_url: str) -> httpx.Response:
        """Скачивает файл Moodle, подставляя токен на своей стороне."""
        # Преподаватели вставляют в курс ссылки на сторонние сайты (canva.link и
        # подобные). Дописать к ним токен — значит отдать доступ к оценкам
        # чужому сервису. Проверка стоит здесь, у самого места подстановки.
        if not self.is_moodle_url(file_url):
            raise ExternalFileRefused(file_url)

        separator = "&" if "?" in file_url else "?"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(f"{file_url}{separator}token={self._token}")
                resp.raise_for_status()
                return resp
        except httpx.HTTPError as exc:
            raise MoodleUnavailable("файл не скачался") from exc
