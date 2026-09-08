"""Ограничение попыток входа.

Вход — единственное место, где можно подбирать чужой пароль от Moodle. Без
ограничения перебор упирается только в скорость сети, а блокировку выдаёт уже
сам Moodle — по учётной записи студента, то есть страдает жертва, а не атакующий.

Счётчик живёт в памяти процесса: gateway один, и терять счётчики при перезапуске
не страшно — окно всего несколько минут. При нескольких экземплярах gateway это
нужно будет вынести в общее хранилище.
"""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> int | None:
        """Возвращает None, если можно, иначе — через сколько секунд повторить."""
        now = time.monotonic()
        hits = self._hits[key]

        while hits and now - hits[0] > self._window:
            hits.popleft()

        if len(hits) >= self._limit:
            return max(1, int(self._window - (now - hits[0])))

        hits.append(now)
        return None

    def reset(self, key: str) -> None:
        """Удачный вход обнуляет счётчик: наказывать нужно перебор, а не забывчивость."""
        self._hits.pop(key, None)

    def sweep(self) -> None:
        """Убирает ключи, по которым давно не стучались, чтобы словарь не рос."""
        now = time.monotonic()
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and now - hits[0] > self._window:
                hits.popleft()
            if not hits:
                del self._hits[key]
