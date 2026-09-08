"""Поход в moodle-service за дедлайнами.

Трекер не ходит в Moodle сам — это зона moodle-service. Сюда передаётся та же
сессия студента, что пришла в запросе.
"""

import httpx

TIMEOUT = httpx.Timeout(30.0)


class MoodleServiceError(Exception):
    """moodle-service ответил не 200. Код нужен, чтобы вернуть его студенту."""

    def __init__(self, status_code: int, detail: str = "") -> None:
        super().__init__(detail or str(status_code))
        self.status_code = status_code
        self.detail = detail


class MoodleServiceClient:
    def __init__(self, base_url: str) -> None:
        self._base = base_url.rstrip("/")

    async def deadlines(self, session_id: str) -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{self._base}/deadlines", headers={"X-Session-Id": session_id}
                )
        except httpx.HTTPError as exc:
            raise MoodleServiceError(503, "сервис Moodle недоступен") from exc

        if resp.status_code != 200:
            # 401 при отозванном токене доносим до студента как есть.
            raise MoodleServiceError(resp.status_code, "не удалось получить дедлайны")
        return resp.json()
