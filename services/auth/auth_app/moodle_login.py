"""Единственное место в проекте, где вообще появляется пароль студента.

Пароль приходит в аргументе, уходит в Moodle по HTTPS и исчезает вместе с кадром
стека. Он не логируется, не возвращается и не сохраняется (SECURITY.md, п. «Пароли»).
"""

import httpx

TOKEN_PATH = "/login/token.php"
REST_PATH = "/webservice/rest/server.php"
SERVICE = "moodle_mobile_app"
TIMEOUT = httpx.Timeout(15.0)


class MoodleAuthError(Exception):
    """Логин/пароль не подошли или Moodle отказал."""


class MoodleUnavailable(Exception):
    """Moodle не ответил — это не вина студента, отвечаем 502."""


async def exchange_password_for_token(site: str, username: str, password: str) -> str:
    """Меняет логин+пароль на токен Moodle Mobile API. Возвращает только токен."""
    params = {"username": username, "password": password, "service": SERVICE}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{site}{TOKEN_PATH}", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        # В текст ошибки может попасть URL с паролем — наружу его не отдаём.
        raise MoodleUnavailable("Moodle недоступен") from exc

    if "token" not in data:
        # Moodle отвечает {"error": "Invalid login, please try again"}
        raise MoodleAuthError(data.get("error") or "неверный логин или пароль")

    # privatetoken не нужен и не сохраняется (SPEC.md §1).
    return data["token"]


async def fetch_site_info(site: str, token: str) -> dict:
    """core_webservice_get_site_info — отсюда берём userid и fullname."""
    params = {
        "wstoken": token,
        "wsfunction": "core_webservice_get_site_info",
        "moodlewsrestformat": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{site}{REST_PATH}", params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise MoodleUnavailable("Moodle недоступен") from exc

    if "exception" in data:
        raise MoodleAuthError(data.get("errorcode", "moodle_error"))

    return data
