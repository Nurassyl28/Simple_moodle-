"""Защита внутренних эндпоинтов.

Наружу опубликован только gateway. Но если кто-то окажется внутри docker-сети,
он не должен уметь дёргать auth-service и получать токены. Поэтому внутренние
вызовы подписываются общим секретом INTERNAL_API_KEY.
"""

import secrets

from fastapi import Header, HTTPException, status

INTERNAL_HEADER = "X-Internal-Key"


def require_internal_key(expected: str):
    """Фабрика зависимости FastAPI: Depends(require_internal_key(cfg.internal_api_key))."""

    async def dependency(x_internal_key: str = Header(default="")) -> None:
        # compare_digest — чтобы по времени ответа нельзя было подобрать ключ.
        if not secrets.compare_digest(x_internal_key, expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="внутренний вызов не подписан",
            )

    return dependency
