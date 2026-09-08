"""moodle-service — всё, что читается из Moodle.

Единственный сервис, который ходит в Moodle. Токен получает у auth-service на
время запроса и наружу не отдаёт: файлы уходят через свой же прокси-эндпоинт,
в ссылке для браузера токена нет (SECURITY.md, п. 4).
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status

from moodle_app.auth_client import AuthClient, AuthUnavailable, SessionInvalid
from moodle_app.client import (
    ExternalFileRefused,
    InvalidToken,
    MoodleClient,
    MoodleError,
    MoodleUnavailable,
)
from moodle_app.config import MoodleConfig
from moodle_app.mapping import courses_from, deadlines_from, files_from, grades_from
from moodle_app.schemas import Deadline, FileItem, Grade, Me
from sduhub_common import FileRefError, make_ref, read_ref, setup_logging

cfg = MoodleConfig()
log = setup_logging(cfg.log_level, cfg.service_name)
auth = AuthClient(cfg.auth_service_url, cfg.internal_api_key)

# Сколько курсов опрашиваем одновременно: Moodle не любит шквал запросов,
# а последовательный обход 8 курсов — это 8 круговых задержек.
COURSE_CONCURRENCY = 4


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("moodle-service запущен, сайт: %s", cfg.moodle_site)
    yield


app = FastAPI(title="SDU Hub — moodle-service", lifespan=lifespan)


class Student:
    """Кто спрашивает и чем ходить в Moodle. Живёт один запрос."""

    def __init__(self, token: str, student_id: str, moodle_userid: int) -> None:
        self.student_id = student_id
        self.moodle_userid = moodle_userid
        self.moodle = MoodleClient(cfg.moodle_site, token)


async def current_student(x_session_id: str = Header(default="")) -> Student:
    if not x_session_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "нужен заголовок X-Session-Id")
    try:
        token, student_id, userid = await auth.token_for(x_session_id)
    except SessionInvalid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "сессия недействительна")
    except AuthUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "сервис входа недоступен")
    return Student(token, student_id, userid)


def _moodle_failure(exc: Exception) -> HTTPException:
    """Один перевод ошибок Moodle в ответы наружу — чтобы не расходились."""
    if isinstance(exc, InvalidToken):
        return HTTPException(status.HTTP_401_UNAUTHORIZED, "требуется повторный вход")
    if isinstance(exc, MoodleUnavailable):
        return HTTPException(status.HTTP_502_BAD_GATEWAY, "Moodle сейчас недоступен")
    code = getattr(exc, "errorcode", "unknown")
    log.warning("Moodle вернул ошибку: %s", code)
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"Moodle отказал: {code}")


async def _gather_by_course(student: Student, worker) -> list:
    """Обходит курсы студента ограниченной пачкой параллельных запросов."""
    try:
        courses = courses_from(await student.moodle.courses(student.moodle_userid))
    except (MoodleError, MoodleUnavailable) as exc:
        raise _moodle_failure(exc)

    semaphore = asyncio.Semaphore(COURSE_CONCURRENCY)

    async def run(course):
        async with semaphore:
            try:
                return await worker(course)
            except (MoodleError, MoodleUnavailable) as exc:
                # Один упавший курс не должен обнулять выдачу по остальным.
                log.warning("курс %s пропущен: %s", course.id, type(exc).__name__)
                return []

    chunks = await asyncio.gather(*(run(c) for c in courses))
    return [item for chunk in chunks for item in chunk]


@app.get("/health")
async def health() -> dict:
    return {"service": cfg.service_name, "site": cfg.moodle_site}


@app.get("/me", response_model=Me)
async def me(student: Student = Depends(current_student)) -> Me:
    try:
        info = await student.moodle.site_info()
        courses = courses_from(await student.moodle.courses(student.moodle_userid))
    except (MoodleError, MoodleUnavailable) as exc:
        raise _moodle_failure(exc)

    return Me(
        fullname=info.get("fullname", ""),
        moodle_userid=student.moodle_userid,
        courses=courses,
    )


@app.get("/grades", response_model=list[Grade])
async def grades(student: Student = Depends(current_student)) -> list[Grade]:
    async def worker(course):
        raw = await student.moodle.grade_items(course.id, student.moodle_userid)
        return grades_from(course.label or course.shortname, raw)

    return await _gather_by_course(student, worker)


@app.get("/files", response_model=list[FileItem])
async def files(student: Student = Depends(current_student)) -> list[FileItem]:
    async def worker(course):
        contents = await student.moodle.course_contents(course.id)
        return files_from(course.label or course.shortname, contents, cfg.moodle_site)

    raw_files = await _gather_by_course(student, worker)

    result = []
    for item in raw_files:
        if item["external"]:
            # Ссылка на сторонний сайт: отдаём как есть, без подписи и без токена.
            result.append(
                FileItem(
                    course=item["course"],
                    section=item["section"],
                    name=item["name"],
                    mimetype=item["mimetype"],
                    modified=item["modified"],
                    external_url=item["fileurl"],
                )
            )
            continue

        result.append(
            FileItem(
                course=item["course"],
                section=item["section"],
                name=item["name"],
                mimetype=item["mimetype"],
                modified=item["modified"],
                download_url="/api/files/download?ref="
                + make_ref(
                    cfg.internal_api_key,
                    student.student_id,
                    item["fileurl"],
                    ttl=cfg.file_ref_ttl_seconds,
                ),
            )
        )
    return result


@app.get("/files/download")
async def download(
    ref: str = Query(min_length=1),
    student: Student = Depends(current_student),
) -> Response:
    """Прокси скачивания: токен подставляется здесь, браузер его не видит."""
    try:
        file_url = read_ref(cfg.internal_api_key, student.student_id, ref)
    except FileRefError as exc:
        # Не уточняем, что именно не так: подпись, владелец или срок.
        log.info("отклонена ссылка на файл: %s", exc)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ссылка недействительна")

    try:
        upstream = await student.moodle.download(file_url)
    except ExternalFileRefused:
        # Подписанная ссылка на чужой домен могла остаться от старой версии.
        # Токен туда не уходит ни при каких обстоятельствах.
        log.warning("отказ качать внешнюю ссылку через прокси")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "внешняя ссылка открывается напрямую"
        )
    except (MoodleError, MoodleUnavailable) as exc:
        raise _moodle_failure(exc)

    headers = {}
    disposition = upstream.headers.get("content-disposition")
    if disposition:
        headers["Content-Disposition"] = disposition

    return Response(
        content=upstream.content,
        media_type=upstream.headers.get("content-type", "application/octet-stream"),
        headers=headers,
    )


@app.get("/deadlines", response_model=list[Deadline])
async def deadlines(student: Student = Depends(current_student)) -> list[Deadline]:
    try:
        raw = await student.moodle.upcoming_events()
    except (MoodleError, MoodleUnavailable) as exc:
        raise _moodle_failure(exc)
    # Пусто в начале семестра — это норма, а не ошибка (README).
    return deadlines_from(raw)
