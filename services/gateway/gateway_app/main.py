"""gateway — единственная публичная точка входа.

Наружу открыт только этот сервис. Он держит сессию в httpOnly-cookie и
подставляет её внутренним сервисам заголовком X-Session-Id. Токена Moodle
gateway не видит вообще: за ним ходит только moodle-service.
"""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sduhub_common import setup_logging

from gateway_app.config import GatewayConfig
from gateway_app.proxy import TIMEOUT, forward
from gateway_app.ratelimit import RateLimiter

cfg = GatewayConfig()
log = setup_logging(cfg.log_level, cfg.service_name)

client: httpx.AsyncClient | None = None
login_limiter = RateLimiter(cfg.login_attempts, cfg.login_window_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global client
    # Один клиент на всё приложение: пул соединений переиспользуется.
    client = httpx.AsyncClient(timeout=TIMEOUT)
    log.info("gateway запущен, разрешённые origin: %s", cfg.allowed_origins)
    yield
    await client.aclose()


app = FastAPI(title="SDU Hub — gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.allowed_origins,
    allow_credentials=True,  # обязательно: сессия ездит в cookie
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Id"],
)


def session_of(request: Request) -> str | None:
    """Cookie — основной способ, заголовок оставлен для curl и мобильных клиентов."""
    return request.cookies.get(cfg.cookie_name) or request.headers.get("X-Session-Id") or None


def require_session(request: Request) -> str:
    session = session_of(request)
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "нужен вход") from None
    return session


@app.get("/api/health")
async def health() -> dict:
    """Состояние всех сервисов разом — чтобы не ходить в каждый руками."""

    async def probe(name: str, url: str) -> tuple[str, bool]:
        try:
            resp = await client.get(f"{url}/health")
            return name, resp.status_code == 200
        except httpx.HTTPError:
            return name, False

    results = await asyncio.gather(
        probe("auth", cfg.auth_service_url),
        probe("moodle", cfg.moodle_service_url),
        probe("tracker", cfg.tracker_service_url),
    )
    services = dict(results)
    return {"service": cfg.service_name, "services": services, "ok": all(services.values())}


def _client_ip(request: Request) -> str:
    """За обратным прокси настоящий адрес приходит в X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/api/login")
async def login(request: Request) -> Response:
    """Логин уходит в auth-service. Сессия возвращается в httpOnly-cookie."""
    body = await request.body()
    try:
        username = (json.loads(body) or {}).get("username", "")
    except ValueError:
        username = ""

    # Считаем и по адресу, и по логину: первое ловит перебор паролей с одной
    # машины, второе — распределённый перебор одной учётной записи.
    keys = [f"ip:{_client_ip(request)}", f"user:{str(username).lower()[:190]}"]
    for key in keys:
        if (retry_after := login_limiter.check(key)) is not None:
            log.warning("слишком много попыток входа, ключ %s", key.split(":", 1)[0])
            return Response(
                content=json.dumps({"detail": "слишком много попыток, попробуй позже"}),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )

    response = await forward(request, cfg.auth_service_url, "/login", None, client)
    if response.status_code == 200:
        for key in keys:
            login_limiter.reset(key)
        session_id = json.loads(response.body)["session_id"]
        # httpOnly: скрипт на странице до сессии не дотянется даже при XSS.
        response.set_cookie(
            cfg.cookie_name,
            session_id,
            httponly=True,
            secure=cfg.cookie_secure,
            samesite=cfg.cookie_samesite,
            max_age=cfg.session_ttl_hours * 3600,
            path="/",
        )
    return response


@app.post("/api/logout")
async def logout(request: Request) -> Response:
    response = await forward(request, cfg.auth_service_url, "/logout", session_of(request), client)
    response.delete_cookie(cfg.cookie_name, path="/")
    return response


@app.delete("/api/account")
async def delete_account(request: Request) -> Response:
    response = await forward(request, cfg.auth_service_url, "/account", session_of(request), client)
    response.delete_cookie(cfg.cookie_name, path="/")
    return response


# --- данные Moodle ---

MOODLE_ROUTES = {
    "/api/me": "/me",
    "/api/grades": "/grades",
    "/api/files": "/files",
    "/api/files/download": "/files/download",
    "/api/deadlines": "/deadlines",
}


@app.get("/api/me")
@app.get("/api/grades")
@app.get("/api/files")
@app.get("/api/files/download")
@app.get("/api/deadlines")
async def moodle_data(request: Request) -> Response:
    session = require_session(request)
    # Путь берём из таблицы, а не из строки запроса: так подставить чужой адрес
    # во внутренний сервис нельзя.
    upstream_path = MOODLE_ROUTES.get(request.url.path.rstrip("/") or request.url.path)
    if upstream_path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "нет такого пути") from None
    return await forward(request, cfg.moodle_service_url, upstream_path, session, client)


# --- трекер ---


@app.api_route("/api/tasks{rest:path}", methods=["GET", "POST", "PATCH", "DELETE"])
async def tasks(request: Request, rest: str = "") -> Response:
    session = require_session(request)
    return await forward(request, cfg.tracker_service_url, f"/tasks{rest}", session, client)


@app.post("/api/deadlines/import", response_model=None)
async def import_deadlines(request: Request) -> Response:
    """Дедлайны Moodle → задачи трекера. Живёт в трекере, туда и уходит."""
    session = require_session(request)
    return await forward(
        request, cfg.tracker_service_url, "/tasks/import-deadlines", session, client
    )


@app.api_route("/api/timetable{rest:path}", methods=["GET", "POST", "DELETE"])
async def timetable(request: Request, rest: str = "") -> Response:
    session = require_session(request)
    return await forward(
        request, cfg.tracker_service_url, f"/timetable{rest}", session, client
    )
