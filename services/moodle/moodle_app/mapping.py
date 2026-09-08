"""Превращение сырых ответов Moodle в то, что показывает фронт.

Чистые функции без сети — их и тестируем. Ответы Moodle разнородные: у части
модулей нет файлов, у части оценок нет значения, поля бывают отсутствуют совсем,
поэтому везде .get с запасным значением.
"""

import re
from urllib.parse import urlparse

from moodle_app.schemas import Course, Deadline, Grade

# Курс в СДУ называется «MAT 156 Discrete Mathematics (Akniyet Mussakhan)», а
# shortname выглядит как «mat156-12418-akniyet.mussakhan-2026-1» — показывать
# студенту ни то, ни другое нельзя. Вытаскиваем код предмета.
COURSE_CODE = re.compile(r"^([A-Z]{2,4})\s?(\d{3})")

# Moodle ставит "-" там, где оценки ещё нет. Показываем как есть, но помечаем.
NO_GRADE = "-"


def course_label(fullname: str, shortname: str) -> str:
    """Короткое имя курса: «MAT 156». Если код не узнан — полное название."""
    match = COURSE_CODE.match((fullname or "").strip())
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return (fullname or shortname or "").strip()


def courses_from(raw: list[dict]) -> list[Course]:
    return [
        Course(
            id=int(c["id"]),
            fullname=c.get("fullname", ""),
            shortname=c.get("shortname", ""),
            label=course_label(c.get("fullname", ""), c.get("shortname", "")),
        )
        for c in raw or []
        if "id" in c
    ]


def grades_from(course_name: str, raw: dict) -> list[Grade]:
    """usergrades[0].gradeitems[] — путь из docs/moodle-api-notes.md."""
    usergrades = (raw or {}).get("usergrades") or []
    if not usergrades:
        return []

    result: list[Grade] = []
    for item in usergrades[0].get("gradeitems") or []:
        grade = item.get("gradeformatted") or NO_GRADE
        grademin, grademax = item.get("grademin"), item.get("grademax")
        result.append(
            Grade(
                course=course_name,
                # itemtype "course" — итог за курс, у него itemname пустой.
                item=item.get("itemname") or ("Итог за курс" if item.get("itemtype") == "course" else ""),
                grade=grade,
                range=f"{_num(grademin)}–{_num(grademax)}" if grademax is not None else None,
                is_total=item.get("itemtype") == "course",
            )
        )
    return result


def _num(value) -> str:
    """Moodle отдаёт границы как 0.00000 — показывать это студенту незачем."""
    if value is None:
        return ""
    number = float(value)
    return str(int(number)) if number == int(number) else f"{number:g}"


def files_from(course_name: str, contents: list[dict], moodle_site: str = "") -> list[dict]:
    """Возвращает сырые записи с fileurl — подписывать ссылки будет вызывающий.

    Помечает ссылки на сторонние сайты: их нельзя качать через прокси, потому
    что прокси подставляет токен.
    """
    moodle_host = urlparse(moodle_site).netloc.lower()
    files: list[dict] = []
    for section in contents or []:
        section_name = section.get("name")
        for module in section.get("modules") or []:
            for item in module.get("contents") or []:
                file_url = item.get("fileurl")
                if not file_url:
                    # У модулей без файлов (форум, задание) contents пустой или без url.
                    continue
                external = bool(moodle_host) and urlparse(file_url).netloc.lower() != moodle_host
                files.append(
                    {
                        "external": external,
                        "course": course_name,
                        "section": section_name,
                        "name": item.get("filename") or module.get("name") or "файл",
                        "mimetype": item.get("mimetype"),
                        "modified": item.get("timemodified"),
                        "fileurl": file_url,
                    }
                )
    return files


def deadlines_from(raw: dict) -> list[Deadline]:
    events = (raw or {}).get("events") or []
    result = [
        Deadline(
            date=int(event["timesort"]),
            # В событии курс приходит тем же уродливым shortname, что и в списке
            # курсов, — приводим к «MAT 156».
            course=course_label(
                (event.get("course") or {}).get("fullname") or "",
                (event.get("course") or {}).get("shortname") or "",
            ),
            name=event.get("name") or "",
            event_id=int(event["id"]) if event.get("id") is not None else None,
        )
        for event in events
        if event.get("timesort") is not None
    ]
    return sorted(result, key=lambda d: d.date)
