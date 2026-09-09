"""Тесты разбора расписания с картинки. Сеть не трогаем — только чистые функции."""

import pytest
from tracker_app.schedule_vision import (
    ALLOWED_MEDIA_TYPES,
    MAX_IMAGE_BYTES,
    ParsedClass,
    VisionUnavailable,
    read_schedule,
    sanitize,
)


def cls(day=0, name="MAT 156", time="08:30", room="F303"):
    return ParsedClass(day=day, name=name, time=time, room=room)


def test_keeps_valid_class():
    (item,) = sanitize([cls()])
    assert (item.day, item.name, item.time, item.room) == (0, "MAT 156", "08:30", "F303")


def test_drops_duplicate_cells():
    """Одна ячейка — одно занятие; повтор в ответе модели не должен дублироваться."""
    assert len(sanitize([cls(), cls()])) == 1


def test_same_course_at_different_times_kept():
    """Пара на две строки таблицы — это две записи, а не повтор."""
    assert len(sanitize([cls(time="09:30"), cls(time="10:30")])) == 2


def test_same_time_different_days_kept():
    assert len(sanitize([cls(day=0), cls(day=3)])) == 2


def test_drops_broken_time():
    """Модель читает картинку и может выдать мусор — в БД он попасть не должен."""
    assert sanitize([cls(time="восемь тридцать")]) == []
    assert sanitize([cls(time="25:00")]) == []
    assert sanitize([cls(time="08:99")]) == []
    assert sanitize([cls(time="")]) == []


def test_drops_empty_name():
    assert sanitize([cls(name="   ")]) == []


def test_normalises_spacing():
    (item,) = sanitize([cls(name="  MAT   156 ", room="  F303 ")])
    assert item.name == "MAT 156" and item.room == "F303"


def test_sorted_by_day_then_time():
    order = sanitize([
        cls(day=4, time="15:30"),
        cls(day=0, time="12:30"),
        cls(day=0, time="09:30"),
    ])
    assert [(c.day, c.time) for c in order] == [(0, "09:30"), (0, "12:30"), (4, "15:30")]


def test_room_may_be_empty():
    (item,) = sanitize([cls(room="")])
    assert item.room == ""


async def test_without_key_is_unavailable():
    """Без ключа сервис поднимается, а функция честно говорит, что выключена."""
    with pytest.raises(VisionUnavailable):
        await read_schedule("", "claude-opus-5", "image/png", b"\x89PNG")


def test_limits_are_sane():
    assert MAX_IMAGE_BYTES == 5 * 1024 * 1024
    assert "image/png" in ALLOWED_MEDIA_TYPES and "application/pdf" not in ALLOWED_MEDIA_TYPES
