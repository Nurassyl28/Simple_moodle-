from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

Kind = Literal["hw", "todo"]
Source = Literal["manual", "moodle"]


class TaskIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    subject: str | None = Field(default=None, max_length=100)
    due: date | None = None
    kind: Kind = "hw"


class TaskPatch(BaseModel):
    """Все поля необязательные — обновляем только присланное."""

    text: str | None = Field(default=None, min_length=1, max_length=500)
    subject: str | None = Field(default=None, max_length=100)
    due: date | None = None
    kind: Kind | None = None
    done: bool | None = None


class Task(BaseModel):
    id: UUID
    text: str
    subject: str | None
    due: date | None
    kind: Kind
    done: bool
    source: Source


class DueGroup(BaseModel):
    due: date
    items: list[Task]


class GroupedTasks(BaseModel):
    """Раскладка как в legacy/homework-tracker.jsx."""

    today: date
    overdue: list[Task]
    due_today: list[Task]
    due_tomorrow: list[Task]
    later: list[DueGroup]
    undated: list[Task]
    done: list[Task]


class ImportRequest(BaseModel):
    raw: str = Field(max_length=50_000)


class ImportResult(BaseModel):
    added: int
    skipped: int


class ClassIn(BaseModel):
    day: int = Field(ge=0, le=6)
    name: str = Field(min_length=1, max_length=100)
    time: time
    room: str | None = Field(default=None, max_length=50)


class ClassItem(ClassIn):
    id: UUID


class DeadlineImportResult(BaseModel):
    """Итог импорта дедлайнов из Moodle."""

    added: int
    updated: int
    total: int


class ParsedClassOut(ClassIn):
    """Занятие, распознанное с картинки. Ещё не сохранено — сначала показываем."""


class ScheduleParseResult(BaseModel):
    classes: list[ParsedClassOut]


class TimetableBulk(BaseModel):
    classes: list[ClassIn] = Field(max_length=100)
    # Расписание чаще заменяют целиком, чем дополняют: новый семестр — новая
    # таблица. Но затирать чужие правки молча нельзя, поэтому это выбор студента.
    replace: bool = False


class HtmlImportRequest(BaseModel):
    """Разметка таблицы, скопированной со страницы расписания портала."""

    html: str = Field(min_length=1, max_length=2_000_000)
