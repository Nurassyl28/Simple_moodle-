"""Работа с БД для auth-service. Токен приходит сюда уже зашифрованным."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
from sduhub_common import Database


class AuthRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert_student(
        self, moodle_userid: int, fullname: str, token_encrypted: bytes
    ) -> UUID:
        """Повторный вход того же студента обновляет токен, а не плодит записи."""
        row = await self._db.fetchrow(
            """
            INSERT INTO students (moodle_userid, fullname, token_encrypted)
            VALUES ($1, $2, $3)
            ON CONFLICT (moodle_userid) DO UPDATE
                SET fullname        = EXCLUDED.fullname,
                    token_encrypted = EXCLUDED.token_encrypted,
                    updated_at      = now()
            RETURNING id
            """,
            moodle_userid,
            fullname,
            token_encrypted,
        )
        return row["id"]

    async def create_session(self, student_id: UUID, ttl_hours: int) -> asyncpg.Record:
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        return await self._db.fetchrow(
            """
            INSERT INTO sessions (student_id, expires_at)
            VALUES ($1, $2)
            RETURNING id, expires_at
            """,
            student_id,
            expires_at,
        )

    async def get_active_session(self, session_id: UUID) -> asyncpg.Record | None:
        """Просроченная сессия не возвращается — считается, что её нет."""
        return await self._db.fetchrow(
            """
            SELECT s.id, s.student_id, st.moodle_userid, st.fullname, st.token_encrypted
            FROM sessions s
            JOIN students st ON st.id = s.student_id
            WHERE s.id = $1 AND s.expires_at > now()
            """,
            session_id,
        )

    async def delete_session(self, session_id: UUID) -> bool:
        result = await self._db.execute("DELETE FROM sessions WHERE id = $1", session_id)
        return result.endswith("1")

    async def forget_student(self, student_id: UUID) -> None:
        """Выход со всех устройств: сессии каскадом, токен из БД стирается."""
        await self._db.execute("DELETE FROM students WHERE id = $1", student_id)

    async def purge_expired_sessions(self) -> int:
        result = await self._db.execute("DELETE FROM sessions WHERE expires_at <= now()")
        return int(result.rsplit(" ", 1)[-1] or 0)
