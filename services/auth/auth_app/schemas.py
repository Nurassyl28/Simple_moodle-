from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Пароль живёт только внутри одного запроса и никуда не записывается."""

    username: str = Field(min_length=1, max_length=190)
    password: str = Field(min_length=1, max_length=190, repr=False)


class LoginResponse(BaseModel):
    session_id: UUID
    expires_at: datetime
    fullname: str


class SessionInfo(BaseModel):
    """Ответ внутреннего эндпоинта. Токена здесь нет намеренно."""

    student_id: UUID
    moodle_userid: int
    fullname: str


class TokenInfo(BaseModel):
    """Только для moodle-service, только по внутреннему ключу."""

    student_id: UUID
    moodle_userid: int
    token: str = Field(repr=False)
