"""Проброс запроса во внутренний сервис.

Gateway ничего не решает по существу — он только приносит ответ сервиса наружу.
Поэтому важно не потерять по дороге код ответа и тело с описанием ошибки.
"""

import httpx
from fastapi import HTTPException, Request, Response, status

TIMEOUT = httpx.Timeout(30.0)

# Заголовки, которые нельзя переносить как есть: их проставляет httpx/сервер,
# иначе получим рассогласование длины или двойное сжатие.
HOP_BY_HOP = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
}


async def forward(
    request: Request,
    base_url: str,
    path: str,
    session_id: str | None,
    client: httpx.AsyncClient,
) -> Response:
    headers = {}
    if session_id:
        headers["X-Session-Id"] = session_id
    if content_type := request.headers.get("content-type"):
        headers["Content-Type"] = content_type

    body = await request.body()

    try:
        upstream = await client.request(
            request.method,
            f"{base_url.rstrip('/')}{path}",
            params=dict(request.query_params),
            content=body or None,
            headers=headers,
        )
    except httpx.HTTPError:
        # Наружу не отдаём ни адрес сервиса, ни текст ошибки httpx.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "сервис временно недоступен"
        ) from None

    passthrough = {
        k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=passthrough,
        media_type=upstream.headers.get("content-type"),
    )
