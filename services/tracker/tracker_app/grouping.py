"""Группировка задач и разбор импорта.

Перенесено из legacy/homework-tracker.jsx один в один: SPEC.md §5 прямо говорит
эту логику переиспользовать, а не писать заново. Функции чистые — тестируются
без БД.
"""

import re
from datetime import date, timedelta

from tracker_app.schemas import DueGroup, GroupedTasks, Task

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def group_tasks(tasks: list[Task], today: date) -> GroupedTasks:
    """Просрочено / Сегодня / Завтра / Дальше / Без даты / Сделано."""
    tomorrow = today + timedelta(days=1)

    open_tasks = [t for t in tasks if not t.done]
    done = [t for t in tasks if t.done]

    overdue = sorted(
        (t for t in open_tasks if t.due and t.due < today), key=lambda t: t.due
    )
    due_today = [t for t in open_tasks if t.due == today]
    due_tomorrow = [t for t in open_tasks if t.due == tomorrow]
    later = sorted(
        (t for t in open_tasks if t.due and t.due > tomorrow), key=lambda t: t.due
    )
    undated = [t for t in open_tasks if not t.due]

    # «Дальше» показывается пачками по дням, как в трекере.
    groups: list[DueGroup] = []
    for task in later:
        if groups and groups[-1].due == task.due:
            groups[-1].items.append(task)
        else:
            groups.append(DueGroup(due=task.due, items=[task]))

    return GroupedTasks(
        today=today,
        overdue=overdue,
        due_today=due_today,
        due_tomorrow=due_tomorrow,
        later=groups,
        undated=undated,
        done=done,
    )


def parse_import(raw: str) -> list[dict]:
    """Строки вида `дата | предмет | задание`.

    Формат из трекера: пустые строки и начинающиеся с # пропускаются, дата строго
    ISO, без текста строка не считается. Две колонки — это дело без предмета.
    """
    result: list[dict] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            due, subject, text = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            due, subject, text = parts[0], "", parts[1]
        else:
            continue

        if not ISO_DATE.match(due) or not text:
            continue
        try:
            due_date = date.fromisoformat(due)
        except ValueError:
            # Формат подошёл, а даты такой нет — 2026-02-31.
            continue

        result.append(
            {
                "due": due_date,
                "subject": subject or None,
                "text": text,
                "kind": "hw" if subject else "todo",
            }
        )
    return result


def dedup_key(due: date | None, subject: str | None, text: str) -> str:
    """Ключ повтора: та же дата, предмет и текст без учёта регистра."""
    return f"{due or ''}|{(subject or '').lower()}|{text.lower()}"


def next_class_for(subject: str, timetable: list[dict], today: date) -> date | None:
    """Ближайший день, когда есть пара по предмету. Подсказка при вводе домашки."""
    days = {item["day"] for item in timetable if item.get("name") == subject}
    if not days:
        return None
    # Смотрим на две недели вперёд: этого хватает, чтобы попасть в любой день.
    for offset in range(1, 15):
        candidate = today + timedelta(days=offset)
        if candidate.weekday() in days:
            return candidate
    return None
