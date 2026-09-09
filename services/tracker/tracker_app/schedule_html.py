"""Разбор расписания, скопированного со страницы Course Schedule портала СДУ.

Расписания пар в Moodle нет — проверено: из 443 доступных функций Web Services
нет ни одной про timetable, а календарь отдаёт только дедлайны. Расписание живёт
в портале, и это HTML-таблица.

Когда таблицу копируют из браузера, в буфер попадает разметка, а не картинка:
столбец = день недели, строка = время, ячейка = занятие. Структуру не нужно
угадывать, поэтому здесь обычный разбор, без распознавания и без внешних сервисов.

Разбор идёт по тексту ячеек, а не по конкретным классам и тегам: вёрстка портала
может поменяться, а «MAT 156» в ячейке под столбцом «We» — нет.
"""

import re
from html.parser import HTMLParser

# «MAT 156», «CSS109», «MDE 003» — код курса.
COURSE_CODE = re.compile(r"\b([A-Z]{2,4})\s?(\d{3})\b")
# «08:30» в первой ячейке строки.
TIME = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
# Аудитория стоит последней, после скобок: «... (ENG 303) F303» → «F303».
ROOM_TAIL = re.compile(r"\)\s*([A-Za-z]{1,3}\s?-?\s?\d{1,4}[A-Za-z]?)\s*$")

# Заголовки столбцов на разных языках. Понедельник — нулевой день.
DAY_HEADERS = {
    "mo": 0, "mon": 0, "monday": 0, "пн": 0, "понедельник": 0,
    "tu": 1, "tue": 1, "tuesday": 1, "вт": 1, "вторник": 1,
    "we": 2, "wed": 2, "wednesday": 2, "ср": 2, "среда": 2,
    "th": 3, "thu": 3, "thursday": 3, "чт": 3, "четверг": 3,
    "fr": 4, "fri": 4, "friday": 4, "пт": 4, "пятница": 4,
    "sa": 5, "sat": 5, "saturday": 5, "сб": 5, "суббота": 5,
    "su": 6, "sun": 6, "sunday": 6, "вс": 6, "воскресенье": 6,
}

MAX_HTML_BYTES = 2 * 1024 * 1024


class ScheduleParseError(ValueError):
    """В присланной разметке не нашлось таблицы расписания."""


class _TableReader(HTMLParser):
    """Собирает таблицы как списки строк, строки — как списки текстов ячеек.

    Ячейки бывают многострочными, поэтому переводы строк сохраняются: время
    начала и окончания стоят на разных строках, и различать их нужно.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._stack: list[list[list[str]]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._stack.append([])
        elif tag == "tr" and self._stack:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._stack:
                self._stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def close(self):
        super().close()
        # Незакрытые теги в буфере обмена — обычное дело; забираем что есть.
        while self._stack:
            self.tables.append(self._stack.pop())


def parse_schedule_html(html: str) -> list[dict]:
    """HTML скопированной таблицы → список занятий."""
    reader = _TableReader()
    reader.feed(html or "")
    reader.close()

    for table in reader.tables:
        classes = _read_table(table)
        if classes:
            return classes

    raise ScheduleParseError("таблица расписания не найдена")


def _read_table(rows: list[list[str]]) -> list[dict]:
    header_index, columns = _find_header(rows)
    if header_index is None:
        return []

    classes: list[dict] = []
    for row in rows[header_index + 1 :]:
        if not row:
            continue
        start = _row_time(row[0])
        if start is None:
            continue

        for position, cell in enumerate(row):
            day = columns.get(position)
            if day is None or not cell.strip():
                continue
            name = _course_code(cell)
            if not name:
                continue
            classes.append(
                {"day": day, "name": name, "time": start, "room": _room(cell)}
            )

    return _dedupe(classes)


def _find_header(rows: list[list[str]]) -> tuple[int | None, dict[int, int]]:
    """Ищет строку с днями недели. Первый столбец — время, он не день."""
    for index, row in enumerate(rows):
        columns = {}
        for position, cell in enumerate(row):
            day = DAY_HEADERS.get(cell.strip().lower())
            if day is not None:
                columns[position] = day
        # Три совпадения — это уже точно шапка, а не случайное «Sa» в тексте.
        if len(columns) >= 3:
            return index, columns
    return None, {}


def _row_time(cell: str) -> str | None:
    """Первое время в ячейке — начало пары. Второе — конец, оно не нужно."""
    match = TIME.search(cell)
    return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


def _course_code(cell: str) -> str:
    match = COURSE_CODE.search(cell)
    return f"{match.group(1)} {match.group(2)}" if match else ""


def _room(cell: str) -> str:
    """Аудитория — то, что стоит после последней закрывающей скобки."""
    for line in reversed([line.strip() for line in cell.splitlines() if line.strip()]):
        match = ROOM_TAIL.search(line)
        if match:
            return " ".join(match.group(1).split())
    return ""


def _dedupe(classes: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    result = []
    for item in classes:
        key = (item["day"], item["name"], item["time"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda c: (c["day"], c["time"]))
