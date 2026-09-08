"""tracker-service — задачи и расписание студента.

В Moodle не ходит: это собственные данные студента. Всё, что делает, ограничено
его student_id.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from sduhub_common import Database, setup_logging

from tracker_app.auth_client import AuthClient, AuthUnavailable, SessionInvalid
from tracker_app.config import TrackerConfig
from tracker_app.grouping import deadline_to_task, dedup_key, group_tasks, parse_import
from tracker_app.moodle_client import MoodleServiceClient, MoodleServiceError
from tracker_app.repository import TrackerRepository
from tracker_app.schemas import (
    ClassIn,
    ClassItem,
    DeadlineImportResult,
    GroupedTasks,
    ImportRequest,
    ImportResult,
    Task,
    TaskIn,
    TaskPatch,
)

cfg = TrackerConfig()
log = setup_logging(cfg.log_level, cfg.service_name)
db = Database(cfg.dsn)
repo = TrackerRepository(db)
auth = AuthClient(cfg.auth_service_url, cfg.internal_api_key)
moodle = MoodleServiceClient(cfg.moodle_service_url)
tz = ZoneInfo(cfg.timezone)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    log.info("tracker-service запущен, часовой пояс: %s", cfg.timezone)
    yield
    await db.close()


app = FastAPI(title="SDU Hub — tracker-service", lifespan=lifespan)


async def current_student(x_session_id: str = Header(default="")) -> UUID:
    if not x_session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "нужен заголовок X-Session-Id") from None
    try:
        return await auth.student_id(x_session_id)
    except SessionInvalid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "сессия недействительна") from None
    except AuthUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "сервис входа недоступен"
        ) from None


def today_local():
    """Дата в поясе студента: в UTC «сегодня» кончается в 5 утра по Алматы."""
    return datetime.now(tz).date()


@app.get("/health")
async def health() -> dict:
    return {"service": cfg.service_name, "db": await db.healthy()}


# --- задачи ---


@app.get("/tasks", response_model=list[Task])
async def list_tasks(student: UUID = Depends(current_student)) -> list[Task]:
    return [Task(**dict(row)) for row in await repo.list_tasks(student)]


@app.get("/tasks/grouped", response_model=GroupedTasks)
async def grouped(student: UUID = Depends(current_student)) -> GroupedTasks:
    tasks = [Task(**dict(row)) for row in await repo.list_tasks(student)]
    return group_tasks(tasks, today_local())


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskIn, student: UUID = Depends(current_student)) -> Task:
    row = await repo.create_task(
        student, payload.text, payload.subject, payload.due, payload.kind
    )
    return Task(**dict(row))


@app.patch("/tasks/{task_id}", response_model=Task)
async def patch_task(
    task_id: UUID, payload: TaskPatch, student: UUID = Depends(current_student)
) -> Task:
    # exclude_unset: отличаем «не прислали поле» от «прислали null».
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "нечего менять") from None

    row = await repo.update_task(student, task_id, changes)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена") from None
    return Task(**dict(row))


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, student: UUID = Depends(current_student)) -> Response:
    if not await repo.delete_task(student, task_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "задача не найдена") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/tasks/import", response_model=ImportResult)
async def import_tasks(
    payload: ImportRequest, student: UUID = Depends(current_student)
) -> ImportResult:
    """Строки `дата | предмет | задание`. Повторы не добавляются."""
    parsed = parse_import(payload.raw)
    seen = {
        dedup_key(row["due"], row["subject"], row["text"])
        for row in await repo.existing_keys(student)
    }

    fresh, skipped = [], 0
    for item in parsed:
        key = dedup_key(item["due"], item["subject"], item["text"])
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        fresh.append(item)

    added = await repo.add_many(student, fresh)
    return ImportResult(added=added, skipped=skipped)


@app.post("/tasks/import-deadlines", response_model=DeadlineImportResult)
async def import_deadlines(x_session_id: str = Header(default="")) -> DeadlineImportResult:
    """Переносит ближайшие дедлайны Moodle в трекер.

    Повторный вызов безопасен: задачи узнаются по id события, перенесённый
    дедлайн обновляет дату, а отметка «сделано» остаётся студенту.
    """
    student = await current_student(x_session_id)
    try:
        events = await moodle.deadlines(x_session_id)
    except MoodleServiceError as exc:
        # 401 (токен отозван) доносим как есть, остальное — как недоступность.
        code = (
            exc.status_code
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(code, exc.detail) from None

    items = [task for task in (deadline_to_task(e, tz) for e in events) if task]
    added, updated = await repo.upsert_moodle_deadlines(student, items)
    log.info("импорт дедлайнов: добавлено %s, обновлено %s", added, updated)
    return DeadlineImportResult(added=added, updated=updated, total=len(items))


# --- расписание ---


@app.get("/timetable", response_model=list[ClassItem])
async def list_classes(student: UUID = Depends(current_student)) -> list[ClassItem]:
    return [ClassItem(**dict(row)) for row in await repo.list_classes(student)]


@app.post("/timetable", response_model=ClassItem, status_code=status.HTTP_201_CREATED)
async def add_class(payload: ClassIn, student: UUID = Depends(current_student)) -> ClassItem:
    row = await repo.add_class(
        student, payload.day, payload.name, payload.time, payload.room
    )
    return ClassItem(**dict(row))


@app.delete("/timetable/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(class_id: UUID, student: UUID = Depends(current_student)) -> Response:
    if not await repo.delete_class(student, class_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "пара не найдена") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
