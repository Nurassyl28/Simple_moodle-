"""Тесты ограничителя попыток входа."""

from gateway_app.ratelimit import RateLimiter


def test_allows_up_to_limit():
    limiter = RateLimiter(limit=3, window_seconds=60)
    assert [limiter.check("ip:1") for _ in range(3)] == [None, None, None]


def test_blocks_after_limit():
    limiter = RateLimiter(limit=3, window_seconds=60)
    for _ in range(3):
        limiter.check("ip:1")
    retry_after = limiter.check("ip:1")
    assert retry_after is not None and retry_after > 0


def test_keys_counted_separately():
    """Перебор с одного адреса не должен блокировать другого студента."""
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.check("ip:1")
    assert limiter.check("ip:2") is None


def test_successful_login_resets():
    """Наказываем перебор, а не забывчивость: удачный вход обнуляет счётчик."""
    limiter = RateLimiter(limit=2, window_seconds=60)
    limiter.check("user:a")
    limiter.check("user:a")
    assert limiter.check("user:a") is not None
    limiter.reset("user:a")
    assert limiter.check("user:a") is None


def test_window_expires():
    limiter = RateLimiter(limit=1, window_seconds=0)
    limiter.check("ip:1")
    assert limiter.check("ip:1") is None


def test_sweep_drops_stale_keys():
    """Иначе словарь растёт на каждый новый адрес и не уменьшается."""
    limiter = RateLimiter(limit=5, window_seconds=0)
    limiter.check("ip:1")
    limiter.sweep()
    assert limiter._hits == {}


def test_sweep_keeps_active_keys():
    limiter = RateLimiter(limit=5, window_seconds=600)
    limiter.check("ip:1")
    limiter.sweep()
    assert "ip:1" in limiter._hits
