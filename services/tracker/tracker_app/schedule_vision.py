"""Распознавание расписания со скриншота портала СДУ.

Студент присылает картинку — таблицу «Course Schedule», где столбцы это дни
недели, строки — пары, а в ячейке лежит код курса, преподаватель и аудитория.
Разбирать такую таблицу обычным OCR бессмысленно: значение несёт положение
ячейки, а не только текст. Поэтому картинку читает Claude с распознаванием
изображений, а ответ приходит по заданной схеме, а не свободным текстом.

Важно: картинка уходит во внешний сервис. Это единственное место в проекте, где
данные студента покидают наш контур, поэтому экран честно предупреждает об этом
до загрузки, а сама картинка нигде не сохраняется.
"""

import asyncio
import base64

import anthropic
from pydantic import BaseModel, Field

# Больше картинка расписания и не бывает; ограничение защищает и нас, и API.
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}

PROMPT = """Перед тобой скриншот расписания занятий студента университета SDU.

Таблица устроена так: столбцы — дни недели (Mo, Tu, We, Th, Fr, Sa), строки —
время пары. В левом столбце указано время начала и окончания, например
«08:30 09:20» — нужно только время начала.

В занятой ячейке написаны: код курса (например «MAT 156», «CSS 109»), полное
название, группа в квадратных скобках, имя преподавателя и место в виде
«Main building - Engineering block: (ENG 303) F303».

Извлеки все занятия. Для каждого верни:
- day: 0 — понедельник (Mo), 1 — вторник, 2 — среда, 3 — четверг, 4 — пятница,
  5 — суббота, 6 — воскресенье;
- name: только код курса с пробелом, например «MAT 156». Не полное название;
- time: время начала пары из левого столбца, в формате HH:MM;
- room: короткий номер аудитории — последнее, что стоит после скобок в описании
  места. Из «Main building - Engineering block: (ENG 303) F303» это «F303»,
  из «Main building: (H 203) H 203» это «H 203». Если аудитории нет, оставь пустым.

Одна ячейка — одна запись. Если один и тот же курс занимает две строки подряд,
верни обе записи, с их собственным временем начала.

Пустые ячейки пропускай. Ничего не придумывай: если ячейку не разобрать,
не включай её."""


class ParsedClass(BaseModel):
    day: int = Field(ge=0, le=6)
    name: str
    time: str
    room: str = ""


class ParsedSchedule(BaseModel):
    classes: list[ParsedClass]


class VisionUnavailable(Exception):
    """Ключ не задан или сервис распознавания не ответил."""


def _extract(api_key: str, model: str, media_type: str, image: bytes) -> ParsedSchedule:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.parse(
        model=model,
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64.standard_b64encode(image).decode(),
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        output_format=ParsedSchedule,
    )
    return response.parsed_output


async def read_schedule(
    api_key: str, model: str, media_type: str, image: bytes
) -> list[ParsedClass]:
    """Возвращает занятия с картинки. Ничего не сохраняет."""
    if not api_key:
        raise VisionUnavailable("распознавание расписания не настроено")

    try:
        # SDK синхронный; уводим вызов в поток, чтобы не блокировать сервис
        # на те секунды, пока читается картинка.
        parsed = await asyncio.to_thread(_extract, api_key, model, media_type, image)
    except anthropic.APIError as exc:
        raise VisionUnavailable("сервис распознавания недоступен") from exc

    return sanitize(parsed.classes)


def sanitize(classes: list[ParsedClass]) -> list[ParsedClass]:
    """Отсекает мусор и повторы.

    Модель читает картинку и может ошибиться, поэтому всё, что уходит в БД,
    проверяется здесь: время должно быть настоящим, название непустым, а один
    и тот же курс в одной клетке не должен попасть дважды.
    """
    result: list[ParsedClass] = []
    seen: set[tuple[int, str, str]] = set()

    for item in classes:
        name = " ".join(item.name.split())
        time = item.time.strip()
        if not name or not _valid_time(time):
            continue

        key = (item.day, name.lower(), time)
        if key in seen:
            continue
        seen.add(key)

        result.append(
            ParsedClass(day=item.day, name=name, time=time, room=" ".join(item.room.split()))
        )

    return sorted(result, key=lambda c: (c.day, c.time))


def _valid_time(value: str) -> bool:
    hours, _, minutes = value.partition(":")
    if not (hours.isdigit() and minutes.isdigit()):
        return False
    return 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59
