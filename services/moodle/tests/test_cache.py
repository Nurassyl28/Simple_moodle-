"""Тесты кэша ответов Moodle."""

from moodle_app.cache import TTLCache


def test_returns_stored_value():
    cache = TTLCache(ttl_seconds=60)
    cache.put(("s1", "grades"), [1, 2])
    assert cache.get(("s1", "grades")) == [1, 2]


def test_miss_returns_none():
    assert TTLCache(60).get(("s1", "grades")) is None


def test_students_do_not_share_cache():
    """Чужие оценки не должны попасть в ответ другому студенту."""
    cache = TTLCache(60)
    cache.put(("s1", "grades"), ["мои"])
    assert cache.get(("s2", "grades")) is None


def test_expired_entry_dropped():
    cache = TTLCache(ttl_seconds=0)
    cache.put(("s1", "grades"), [1])
    assert cache.get(("s1", "grades")) is None


def test_drop_student_clears_everything_of_theirs():
    """После выхода данные студента держать незачем."""
    cache = TTLCache(60)
    cache.put(("s1", "grades"), [1])
    cache.put(("s1", "files"), [2])
    cache.put(("s2", "grades"), [3])
    cache.drop_student("s1")
    assert cache.get(("s1", "grades")) is None
    assert cache.get(("s1", "files")) is None
    assert cache.get(("s2", "grades")) == [3]


def test_size_is_bounded():
    """Иначе кэш растёт вместе с числом студентов и не уменьшается."""
    cache = TTLCache(ttl_seconds=60, max_entries=10)
    for i in range(50):
        cache.put((f"s{i}", "grades"), i)
    assert len(cache._data) <= 10
