"""Тесты разбора ответов Moodle. Сети здесь нет — только чистые функции."""

import pytest
from moodle_app.client import ExternalFileRefused, MoodleClient
from moodle_app.mapping import (
    course_label,
    courses_from,
    deadlines_from,
    files_from,
    grades_from,
)


def test_courses_basic():
    courses = courses_from([{"id": 7, "fullname": "Дискретная математика", "shortname": "MAT 156"}])
    assert (courses[0].id, courses[0].shortname) == (7, "MAT 156")


def test_course_without_id_skipped():
    assert courses_from([{"fullname": "битая запись"}]) == []


def test_courses_handles_none():
    assert courses_from(None) == []


def test_grades_path_and_total():
    """Путь usergrades[0].gradeitems[] и пометка итога за курс."""
    raw = {
        "usergrades": [
            {
                "gradeitems": [
                    {"itemname": "Лаба 1", "itemtype": "mod", "gradeformatted": "8,00",
                     "grademin": 0.0, "grademax": 10.0},
                    {"itemname": None, "itemtype": "course", "gradeformatted": "-",
                     "grademin": 0.0, "grademax": 100.0},
                ]
            }
        ]
    }
    lab, total = grades_from("CSS 109", raw)
    assert (lab.item, lab.grade, lab.range, lab.is_total) == ("Лаба 1", "8,00", "0–10", False)
    assert (total.item, total.grade, total.is_total) == ("Итог за курс", "-", True)


def test_grades_empty_payload():
    """В начале семестра оценок нет — это норма, не ошибка."""
    assert grades_from("CSS 109", {"usergrades": []}) == []
    assert grades_from("CSS 109", {}) == []


def test_grade_range_without_decimals():
    raw = {"usergrades": [{"gradeitems": [
        {"itemname": "Тест", "itemtype": "mod", "gradeformatted": "5,5",
         "grademin": 0.00000, "grademax": 12.50000}]}]}
    assert grades_from("C", raw)[0].range == "0–12.5"


def test_files_skips_modules_without_url():
    """У форумов и заданий файлов нет — такие модули пропускаем."""
    contents = [
        {"name": "Тема 1", "modules": [
            {"name": "Форум", "modname": "forum", "contents": []},
            {"name": "Лекция", "modname": "resource", "contents": [
                {"filename": "lecture1.pdf", "fileurl": "https://m/pluginfile.php/1/x.pdf",
                 "mimetype": "application/pdf", "timemodified": 1757000000},
                {"filename": "без ссылки", "fileurl": ""},
            ]},
        ]}
    ]
    files = files_from("CSS 112", contents)
    assert len(files) == 1
    assert files[0]["name"] == "lecture1.pdf"
    assert files[0]["section"] == "Тема 1"


def test_files_handles_missing_keys():
    assert files_from("C", [{"name": "Тема"}]) == []
    assert files_from("C", None) == []


def test_deadlines_sorted_and_mapped():
    raw = {"events": [
        {"id": 22, "name": "Лаба 2", "timesort": 1760000000, "course": {"shortname": "CSS 112"}},
        {"id": 11, "name": "Лаба 1", "timesort": 1750000000, "course": {"shortname": "CSS 109"}},
    ]}
    first, second = deadlines_from(raw)
    assert first.name == "Лаба 1"
    assert second.date > first.date
    assert first.event_id == 11


def test_deadlines_empty_is_normal():
    assert deadlines_from({"events": []}) == []
    assert deadlines_from({}) == []


def test_deadline_without_course_does_not_crash():
    raw = {"events": [{"id": 1, "name": "Событие", "timesort": 1750000000}]}
    assert deadlines_from(raw)[0].course == ""


def test_deadline_without_timesort_skipped():
    assert deadlines_from({"events": [{"id": 1, "name": "Без даты"}]}) == []


# --- находки живого запуска ---


SITE = "https://moodle.sdu.edu.kz"


def test_course_label_extracts_code():
    """Живой курс: «MAT 156 Discrete Mathematics (Akniyet Mussakhan)»."""
    label = course_label("MAT 156 Discrete Mathematics (Akniyet Mussakhan)", "mat156-12418")
    assert label == "MAT 156"


def test_course_label_without_space():
    assert course_label("CSS109 Programming", "x") == "CSS 109"


def test_course_label_falls_back_to_fullname():
    assert course_label("Военная кафедра", "vk-2026") == "Военная кафедра"


def test_course_label_falls_back_to_shortname():
    assert course_label("", "mde003-11096") == "mde003-11096"


def test_courses_get_label():
    (course,) = courses_from(
        [{"id": 1, "fullname": "MDE 003 General English (B1 level)", "shortname": "mde003-11096"}]
    )
    assert course.label == "MDE 003"


def test_external_file_marked():
    """Преподаватель вставил ссылку на canva.link — токен туда отправлять нельзя."""
    contents = [{"name": "Тема 1", "modules": [{"name": "Unit 1 ppt", "contents": [
        {"filename": "Unit 1 ppt", "fileurl": "https://canva.link/d54flvbd"},
    ]}]}]
    (item,) = files_from("MDE 003", contents, SITE)
    assert item["external"] is True


def test_moodle_file_not_marked_external():
    contents = [{"name": "Тема 1", "modules": [{"name": "Лекция", "contents": [
        {"filename": "l.pdf", "fileurl": "https://moodle.sdu.edu.kz/webservice/pluginfile.php/1/l.pdf"},
    ]}]}]
    (item,) = files_from("MAT 156", contents, SITE)
    assert item["external"] is False


def test_client_refuses_external_download():
    """Главная защита: токен не подставляется к чужому хосту."""
    import asyncio

    client = MoodleClient(SITE, "a1b2c3d4e5f60718293a4b5c6d7e8f90")
    with pytest.raises(ExternalFileRefused):
        asyncio.run(client.download("https://canva.link/no1j8tql"))


def test_client_recognises_own_host():
    client = MoodleClient(SITE, "token")
    assert client.is_moodle_url("https://moodle.sdu.edu.kz/webservice/pluginfile.php/1/x.pdf")
    assert not client.is_moodle_url("https://moodle.sdu.edu.kz.evil.com/x.pdf")
