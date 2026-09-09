"""Тесты разбора таблицы расписания, скопированной из портала СДУ.

Образец собран по реальной странице Course Schedule: те же заголовки, то же
устройство ячейки, те же формы записи аудитории.
"""

import pytest
from tracker_app.schedule_html import ScheduleParseError, parse_schedule_html


def cell(code, title, teacher, place):
    return (
        f'<td><a href="#"><b>{code}</b></a> {title} (2+2+0) [4cr / 5ECTS]<br>'
        f"[08-P]<br>{teacher}<br>\N{HOUSE BUILDING}: {place}</td>"
    )


ENG303 = "Main building - Engineering block: (ENG 303) F303"
ENG101 = "Main building - Engineering block: (ENG 101) F101"
LABEN1 = "Main building - Engineering block: (LAB-EN1) F108"
LT_A1 = "Main building: (L.T. A1) D117"
H203 = "Main building: (H 203) H 203"

SDU_TABLE = f"""
<table>
  <tr><th>Day/Hour</th><th>Mo</th><th>Tu</th><th>We</th><th>Th</th><th>Fr</th><th>Sa</th></tr>
  <tr>
    <td><b>08:30</b><br>09:20</td>
    <td></td>
    {cell("MDE 003", "General English (B1 level)", "Aigerim Orynbassarova", H203)}
    {cell("MAT 156", "Discrete Mathematics", "Nurlan Yerkinbayev, PhD", LT_A1)}
    <td></td>
    {cell("CSS 312", "Computer Networks 1", "Nurbol Moldabay", LABEN1)}
    <td></td>
  </tr>
  <tr>
    <td><b>09:30</b><br>10:20</td>
    {cell("CSS 109", "Calculus 1", "Kamilla Zhamalbekova", ENG303)}
    <td></td>
    {cell("MAT 156", "Discrete Mathematics", "Nurlan Yerkinbayev, PhD", LT_A1)}
    {cell("CSS 112", "Physics 1", "Balziya Maldybay", ENG101)}
    {cell("CSS 312", "Computer Networks 1", "Nurbol Moldabay", LABEN1)}
    <td></td>
  </tr>
  <tr>
    <td><b>10:30</b><br>11:20</td>
    {cell("CSS 109", "Calculus 1", "Kamilla Zhamalbekova", ENG303)}
    <td></td><td></td><td></td><td></td><td></td>
  </tr>
</table>
"""


def test_reads_all_classes():
    classes = parse_schedule_html(SDU_TABLE)
    assert len(classes) == 8


def test_maps_columns_to_days():
    """Смысл несёт столбец: CSS 312 стоит под Fr, значит пятница."""
    classes = parse_schedule_html(SDU_TABLE)
    css312 = [c for c in classes if c["name"] == "CSS 312"]
    assert {c["day"] for c in css312} == {4}


def test_takes_start_time_not_end():
    """В ячейке времени две отметки: начало и конец. Нужна первая."""
    classes = parse_schedule_html(SDU_TABLE)
    assert {c["time"] for c in classes} <= {"08:30", "09:30", "10:30"}
    assert all(c["time"] != "09:20" for c in classes)


def test_course_code_normalised():
    classes = parse_schedule_html(SDU_TABLE)
    assert "MAT 156" in {c["name"] for c in classes}
    # Полное название курса в имя не попадает.
    assert all("Discrete" not in c["name"] for c in classes)


def test_room_after_last_bracket():
    classes = parse_schedule_html(SDU_TABLE)
    rooms = {(c["name"], c["room"]) for c in classes}
    assert ("CSS 109", "F303") in rooms
    assert ("CSS 312", "F108") in rooms
    assert ("MAT 156", "D117") in rooms


def test_room_when_place_repeats_code():
    """«Main building: (H 203) H 203» — аудитория «H 203», а не «(H 203)»."""
    (mde,) = [c for c in parse_schedule_html(SDU_TABLE) if c["name"] == "MDE 003"]
    assert mde["room"] == "H 203"


def test_two_row_class_kept_as_two():
    """Пара на две строки таблицы — два занятия с разным началом."""
    css109 = [c for c in parse_schedule_html(SDU_TABLE) if c["name"] == "CSS 109"]
    assert sorted(c["time"] for c in css109) == ["09:30", "10:30"]


def test_sorted_by_day_then_time():
    classes = parse_schedule_html(SDU_TABLE)
    assert classes == sorted(classes, key=lambda c: (c["day"], c["time"]))


def test_empty_cells_skipped():
    assert all(c["name"] for c in parse_schedule_html(SDU_TABLE))


def test_russian_headers():
    html = """<table>
      <tr><td>Время</td><td>Пн</td><td>Вт</td><td>Ср</td></tr>
      <tr><td>09:30 10:20</td><td>CSS 109 Calculus</td><td></td><td>MAT 156 Discrete</td></tr>
    </table>"""
    classes = parse_schedule_html(html)
    assert [(c["day"], c["name"]) for c in classes] == [(0, "CSS 109"), (2, "MAT 156")]


def test_picks_schedule_table_among_others():
    """В буфер вместе с расписанием часто попадают соседние таблицы вёрстки."""
    html = "<table><tr><td>меню</td><td>вход</td></tr></table>" + SDU_TABLE
    assert len(parse_schedule_html(html)) == 8


def test_without_table_raises():
    with pytest.raises(ScheduleParseError):
        parse_schedule_html("<p>просто текст</p>")


def test_without_day_headers_raises():
    with pytest.raises(ScheduleParseError):
        parse_schedule_html("<table><tr><td>a</td><td>b</td></tr></table>")


def test_empty_input_raises():
    with pytest.raises(ScheduleParseError):
        parse_schedule_html("")
