"""Тесты обмена логина на токен. Сеть подменена, реальный Moodle не трогаем."""

import httpx
import pytest
from auth_app import moodle_login
from auth_app.moodle_login import (
    MoodleAuthError,
    MoodleUnavailable,
    exchange_password_for_token,
    fetch_site_info,
)

SITE = "https://moodle.sdu.edu.kz"
TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f90"


@pytest.fixture
def fake_moodle(monkeypatch):
    """Подменяет httpx.AsyncClient на клиент с заданным ответом."""

    def install(handler):
        transport = httpx.MockTransport(handler)

        class Client(httpx.AsyncClient):
            def __init__(self, *args, **kwargs):
                kwargs["transport"] = transport
                super().__init__(*args, **kwargs)

        monkeypatch.setattr(moodle_login.httpx, "AsyncClient", Client)

    return install


async def test_returns_token(fake_moodle):
    fake_moodle(lambda r: httpx.Response(200, json={"token": TOKEN, "privatetoken": "p"}))
    assert await exchange_password_for_token(SITE, "260107019", "pass") == TOKEN


async def test_privatetoken_not_returned(fake_moodle):
    """SPEC.md §1: privatetoken не нужен и не должен уходить дальше."""
    fake_moodle(lambda r: httpx.Response(200, json={"token": TOKEN, "privatetoken": "секрет"}))
    result = await exchange_password_for_token(SITE, "u", "p")
    assert result == TOKEN and "секрет" not in result


async def test_wrong_password_raises_auth_error(fake_moodle):
    fake_moodle(lambda r: httpx.Response(200, json={"error": "Invalid login, please try again"}))
    with pytest.raises(MoodleAuthError):
        await exchange_password_for_token(SITE, "u", "неверный")


async def test_password_not_in_error_text(fake_moodle):
    """В тексте ошибки httpx лежит URL с паролем — наружу он попасть не должен."""

    def boom(request):
        raise httpx.ConnectError("не достучались", request=request)

    fake_moodle(boom)
    with pytest.raises(MoodleUnavailable) as exc:
        await exchange_password_for_token(SITE, "u", "СуперПароль123")
    assert "СуперПароль123" not in str(exc.value)


async def test_site_info_parsed(fake_moodle):
    fake_moodle(
        lambda r: httpx.Response(200, json={"userid": 14614, "fullname": "Тест Тестов"})
    )
    info = await fetch_site_info(SITE, TOKEN)
    assert info["userid"] == 14614


async def test_site_info_exception_becomes_auth_error(fake_moodle):
    """Moodle отвечает 200 и на ошибку тоже — важно не принять её за успех."""
    fake_moodle(lambda r: httpx.Response(200, json={"exception": "x", "errorcode": "invalidtoken"}))
    with pytest.raises(MoodleAuthError):
        await fetch_site_info(SITE, TOKEN)


async def test_server_error_is_unavailable(fake_moodle):
    fake_moodle(lambda r: httpx.Response(503))
    with pytest.raises(MoodleUnavailable):
        await exchange_password_for_token(SITE, "u", "p")
