"""auth-service — вход в Moodle, хранение токена, сессии.

Единственный сервис, который видит пароль студента, и единственный, кто умеет
расшифровать его токен. Наружу токен не отдаётся никогда — только внутренним
вызовом с подписью INTERNAL_API_KEY.
"""

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status

from auth_app.config import AuthConfig
from auth_app.moodle_login import (
    MoodleAuthError,
    MoodleUnavailable,
    exchange_password_for_token,
    fetch_site_info,
)
from auth_app.repository import AuthRepository
from auth_app.schemas import LoginRequest, LoginResponse, SessionInfo, TokenInfo
from sduhub_common import Database, TokenCipher, require_internal_key, setup_logging

cfg = AuthConfig()
log = setup_logging(cfg.log_level, cfg.service_name)
db = Database(cfg.dsn)
cipher = TokenCipher(cfg.token_encryption_key)
repo = AuthRepository(db)
internal_only = require_internal_key(cfg.internal_api_key)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.connect()
    removed = await repo.purge_expired_sessions()
    log.info("auth-service запущен, просроченных сессий удалено: %s", removed)
    yield
    await db.close()


app = FastAPI(title="SDU Hub — auth-service", lifespan=lifespan)


async def session_from_header(x_session_id: str = Header(default="")) -> UUID:
    try:
        return UUID(x_session_id)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "нужен заголовок X-Session-Id")


@app.get("/health")
async def health() -> dict:
    return {"service": cfg.service_name, "db": await db.healthy()}


@app.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    """Обмен логина на токен. Пароль не логируется и не сохраняется."""
    try:
        token = await exchange_password_for_token(
            cfg.moodle_site, payload.username, payload.password
        )
        info = await fetch_site_info(cfg.moodle_site, token)
    except MoodleAuthError:
        # Причину не уточняем: не подсказываем перебору, существует ли логин.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "неверный логин или пароль")
    except MoodleUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Moodle сейчас недоступен")

    student_id = await repo.upsert_student(
        moodle_userid=int(info["userid"]),
        fullname=info.get("fullname", ""),
        token_encrypted=cipher.encrypt(token),
    )
    session = await repo.create_session(student_id, cfg.session_ttl_hours)

    log.info("вход выполнен: student=%s", student_id)
    return LoginResponse(
        session_id=session["id"],
        expires_at=session["expires_at"],
        fullname=info.get("fullname", ""),
    )


@app.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session_id: UUID = Depends(session_from_header)) -> Response:
    await repo.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(session_id: UUID = Depends(session_from_header)) -> Response:
    """Удаление аккаунта: токен и все данные студента стираются (SECURITY.md)."""
    row = await repo.get_active_session(session_id)
    if row is not None:
        await repo.forget_student(row["student_id"])
        log.info("аккаунт удалён: student=%s", row["student_id"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/internal/session/{session_id}",
    response_model=SessionInfo,
    dependencies=[Depends(internal_only)],
)
async def internal_session(session_id: UUID) -> SessionInfo:
    """Кто стоит за сессией. Токена в ответе нет — для него отдельный эндпоинт."""
    row = await repo.get_active_session(session_id)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "сессия недействительна")
    return SessionInfo(
        student_id=row["student_id"],
        moodle_userid=row["moodle_userid"],
        fullname=row["fullname"],
    )


@app.get(
    "/internal/token/{session_id}",
    response_model=TokenInfo,
    dependencies=[Depends(internal_only)],
)
async def internal_token(session_id: UUID) -> TokenInfo:
    """Расшифрованный токен Moodle. Вызывает только moodle-service."""
    row = await repo.get_active_session(session_id)
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "сессия недействительна")
    try:
        token = cipher.decrypt(row["token_encrypted"])
    except Exception:
        # Обычно значит, что сменили TOKEN_ENCRYPTION_KEY. Просим войти заново.
        log.warning("токен не расшифрован: student=%s", row["student_id"])
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "требуется повторный вход")

    return TokenInfo(
        student_id=row["student_id"],
        moodle_userid=row["moodle_userid"],
        token=token,
    )
