"""Тесты группировки и импорта. Перенос логики из legacy/homework-tracker.jsx."""

from datetime import date
from uuid import uuid4
from zoneinfo import ZoneInfo

from tracker_app.grouping import (
    deadline_to_task,
    dedup_key,
    group_tasks,
    next_class_for,
    parse_import,
)
from tracker_app.schemas import Task

TODAY = date(2026, 9, 8)  # вторник


def task(text, due=None, done=False, subject=None, kind="hw"):
    return Task(
        id=uuid4(), text=text, subject=subject, due=due, kind=kind, done=done, source="manual"
    )


def test_splits_into_buckets():
    grouped = group_tasks(
        [
            task("просрочено", date(2026, 9, 5)),
            task("сегодня", TODAY),
            task("завтра", date(2026, 9, 9)),
            task("позже", date(2026, 9, 20)),
            task("без даты"),
            task("сделано", TODAY, done=True),
        ],
        TODAY,
    )
    assert [t.text for t in grouped.overdue] == ["просрочено"]
    assert [t.text for t in grouped.due_today] == ["сегодня"]
    assert [t.text for t in grouped.due_tomorrow] == ["завтра"]
    assert [t.text for t in grouped.undated] == ["без даты"]
    assert [t.text for t in grouped.done] == ["сделано"]


def test_done_task_leaves_its_bucket():
    """Выполненная задача не должна висеть в «сегодня»."""
    grouped = group_tasks([task("готово", TODAY, done=True)], TODAY)
    assert grouped.due_today == []
    assert len(grouped.done) == 1


def test_overdue_sorted_oldest_first():
    grouped = group_tasks(
        [task("вчера", date(2026, 9, 7)), task("неделю назад", date(2026, 9, 1))], TODAY
    )
    assert [t.text for t in grouped.overdue] == ["неделю назад", "вчера"]


def test_later_grouped_by_day():
    grouped = group_tasks(
        [
            task("а", date(2026, 9, 15)),
            task("б", date(2026, 9, 15)),
            task("в", date(2026, 9, 20)),
        ],
        TODAY,
    )
    assert [len(g.items) for g in grouped.later] == [2, 1]
    assert grouped.later[0].due == date(2026, 9, 15)


def test_empty_input():
    grouped = group_tasks([], TODAY)
    assert grouped.overdue == [] and grouped.later == [] and grouped.today == TODAY


# --- импорт ---


def test_import_three_columns():
    (item,) = parse_import("2026-09-10 | CSS 109 | Лаба 3")
    assert item == {"due": date(2026, 9, 10), "subject": "CSS 109", "text": "Лаба 3", "kind": "hw"}


def test_import_two_columns_is_todo():
    """Без предмета это личное дело, а не домашка."""
    (item,) = parse_import("2026-09-10 | забрать справку")
    assert item["subject"] is None and item["kind"] == "todo"


def test_import_skips_comments_and_blanks():
    assert parse_import("# заметка\n\n   \n2026-09-10 | X | Y") == [
        {"due": date(2026, 9, 10), "subject": "X", "text": "Y", "kind": "hw"}
    ]


def test_import_rejects_bad_date_format():
    assert parse_import("10.09.2026 | CSS 109 | Лаба") == []


def test_import_rejects_nonexistent_date():
    """Формат подходит, а даты такой нет."""
    assert parse_import("2026-02-31 | CSS 109 | Лаба") == []


def test_import_rejects_empty_text():
    assert parse_import("2026-09-10 | CSS 109 | ") == []


def test_import_handles_empty_input():
    assert parse_import("") == [] and parse_import(None) == []


def test_dedup_key_ignores_case():
    assert dedup_key(date(2026, 9, 10), "CSS 109", "Лаба") == dedup_key(
        date(2026, 9, 10), "css 109", "лаба"
    )


def test_dedup_key_separates_subjects():
    assert dedup_key(date(2026, 9, 10), "CSS 109", "Лаба") != dedup_key(
        date(2026, 9, 10), "MAT 156", "Лаба"
    )


# --- подсказка следующей пары ---


def test_next_class_finds_nearest_day():
    """Вторник; пары по CSS 109 в понедельник и пятницу — ближайшая пятница."""
    timetable = [{"day": 0, "name": "CSS 109"}, {"day": 4, "name": "CSS 109"}]
    assert next_class_for("CSS 109", timetable, TODAY) == date(2026, 9, 11)


def test_next_class_wraps_to_next_week():
    assert next_class_for("CSS 109", [{"day": 0, "name": "CSS 109"}], TODAY) == date(2026, 9, 14)


def test_next_class_unknown_subject():
    assert next_class_for("MDE 003", [{"day": 0, "name": "CSS 109"}], TODAY) is None


# --- импорт дедлайнов Moodle ---



ALMATY = ZoneInfo("Asia/Almaty")


def test_deadline_converted_to_task():
    event = {"date": 1757000000, "course": "CSS 112", "name": "Сдать лабу 2", "event_id": 42}
    task = deadline_to_task(event, ALMATY)
    assert task["text"] == "Сдать лабу 2"
    assert task["subject"] == "CSS 112"
    assert task["moodle_event_id"] == 42
    assert task["kind"] == "hw"


def test_deadline_date_uses_student_timezone():
    """Дедлайн 04:00 по Алматы в UTC ещё вчерашний — дата должна быть местная."""
    # 2026-09-09 04:00 по Алматы = 2026-09-08 23:00 UTC
    task = deadline_to_task({"date": 1789081200, "name": "Дедлайн", "event_id": 1}, ALMATY)
    utc_task = deadline_to_task(
        {"date": 1789081200, "name": "Дедлайн", "event_id": 1}, ZoneInfo("UTC")
    )
    assert task["due"] != utc_task["due"]
    assert task["due"] > utc_task["due"]


def test_deadline_without_name_skipped():
    assert deadline_to_task({"date": 1757000000, "name": "  ", "event_id": 1}, ALMATY) is None


def test_deadline_without_date_skipped():
    assert deadline_to_task({"name": "Без даты", "event_id": 1}, ALMATY) is None


def test_deadline_without_course_has_no_subject():
    task = deadline_to_task(
        {"date": 1757000000, "course": "", "name": "X", "event_id": 1}, ALMATY
    )
    assert task["subject"] is None
