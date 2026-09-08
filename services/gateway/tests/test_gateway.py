"""Тесты gateway без сети: разбор настроек и фильтрация заголовков."""

import pytest
from gateway_app.config import GatewayConfig
from gateway_app.proxy import HOP_BY_HOP

BASE = dict(
    postgres_user="u",
    postgres_password="p",
    postgres_db="d",
    token_encryption_key="k",
    internal_api_key="i",
)


def cfg(**extra) -> GatewayConfig:
    # _env_file=None обязателен: иначе тест читает .env разработчика и падает
    # или проходит по чужим значениям.
    return GatewayConfig(_env_file=None, **BASE, **extra)


def test_origins_split_and_trimmed():
    parsed = cfg(cors_origins="http://a ,http://b,  http://c ").allowed_origins
    assert parsed == ["http://a", "http://b", "http://c"]


def test_empty_origins_give_empty_list():
    """Пустой список — это «никому», а не «всем»."""
    assert cfg(cors_origins="").allowed_origins == []
    assert cfg(cors_origins=" , ").allowed_origins == []


def test_samesite_normalised():
    assert cfg(cookie_samesite="Lax").cookie_samesite == "lax"


def test_bad_samesite_rejected_on_start():
    """Опечатка в настройке должна валить сервис на старте, а не тихо ломать вход."""
    with pytest.raises(ValueError):
        cfg(cookie_samesite="ага")


def test_cookie_secure_by_default():
    """Небезопасную cookie включают осознанно, только для локальной разработки."""
    assert cfg().cookie_secure is True


def test_hop_by_hop_headers_not_forwarded():
    """Перенос этих заголовков ломает длину тела и даёт двойное сжатие."""
    assert {"content-length", "content-encoding", "transfer-encoding"} <= HOP_BY_HOP
