from pydantic import BaseModel


class Course(BaseModel):
    id: int
    fullname: str
    shortname: str
    # Короткое имя для экрана: «MAT 156».
    label: str = ""


class Me(BaseModel):
    fullname: str
    moodle_userid: int
    courses: list[Course]


class Grade(BaseModel):
    course: str
    item: str
    grade: str
    range: str | None = None
    is_total: bool = False


class FileItem(BaseModel):
    course: str
    section: str | None = None
    name: str
    mimetype: str | None = None
    modified: int | None = None
    # Подписанная ссылка на свой же бэкенд. Токена Moodle в ней нет.
    # Пусто у внешних ссылок — их мы не проксируем.
    download_url: str | None = None
    # Ссылка на сторонний сайт, вставленная преподавателем. Открывается как есть,
    # без токена: отдавать токен чужому домену нельзя.
    external_url: str | None = None


class Deadline(BaseModel):
    date: int
    course: str
    name: str
    event_id: int | None = None
