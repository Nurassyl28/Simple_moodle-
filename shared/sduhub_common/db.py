"""Пул соединений с Postgres. Один на сервис, живёт всё время работы приложения."""

import asyncpg


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self, min_size: int = 1, max_size: int = 10) -> None:
        self._pool = await asyncpg.create_pool(
            self._dsn, min_size=min_size, max_size=max_size
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("пул не инициализирован: вызови connect() на старте")
        return self._pool

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def healthy(self) -> bool:
        try:
            return await self.fetchrow("SELECT 1") is not None
        except Exception:
            return False
