"""Короткий кэш ответов Moodle.

Экран «Оценки» при восьми курсах — это восемь запросов в Moodle на каждое
открытие. Студент листает вкладки туда-сюда, и без кэша университетский сервер
получает нагрузку на ровном месте.

Кэш живёт в памяти процесса и короткий: минута. Свежесть оценок при этом не
страдает — они меняются реже, чем раз в минуту.
"""

import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int = 1000) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._data: dict[tuple, tuple[float, Any]] = {}

    def get(self, key: tuple) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > self._ttl:
            del self._data[key]
            return None
        return value

    def put(self, key: tuple, value: Any) -> None:
        if len(self._data) >= self._max:
            self._evict_stale()
        self._data[key] = (time.monotonic(), value)

    def drop_student(self, student_id: str) -> None:
        """После выхода или удаления аккаунта чужие данные держать незачем."""
        for key in [k for k in self._data if k and k[0] == student_id]:
            del self._data[key]

    def _evict_stale(self) -> None:
        now = time.monotonic()
        stale = [k for k, (at, _) in self._data.items() if now - at > self._ttl]
        for key in stale:
            del self._data[key]
        if len(self._data) >= self._max:
            # Всё ещё полно живых записей — выбрасываем самую старую.
            oldest = min(self._data, key=lambda k: self._data[k][0])
            del self._data[oldest]
