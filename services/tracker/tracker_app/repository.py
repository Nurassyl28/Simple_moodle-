"""Работа с БД трекера. Любой запрос ограничен student_id — чужое не видно."""

from datetime import date
from uuid import UUID

import asyncpg

from sduhub_common import Database

TASK_FIELDS = "id, text, subject, due, kind, done, source"


class TrackerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    # --- задачи ---

    async def list_tasks(self, student_id: UUID) -> list[asyncpg.Record]:
        return await self._db.fetch(
            f"SELECT {TASK_FIELDS} FROM tasks WHERE student_id = $1"
            " ORDER BY due NULLS LAST, created_at",
            student_id,
        )

    async def create_task(
        self,
        student_id: UUID,
        text: str,
        subject: str | None,
        due: date | None,
        kind: str,
        source: str = "manual",
        moodle_event_id: int | None = None,
    ) -> asyncpg.Record:
        return await self._db.fetchrow(
            f"""
            INSERT INTO tasks (student_id, text, subject, due, kind, source, moodle_event_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING {TASK_FIELDS}
            """,
            student_id,
            text,
            subject,
            due,
            kind,
            source,
            moodle_event_id,
        )

    async def update_task(
        self, student_id: UUID, task_id: UUID, changes: dict
    ) -> asyncpg.Record | None:
        """COALESCE вместо сборки SQL строками: не присланное поле остаётся как было."""
        return await self._db.fetchrow(
            f"""
            UPDATE tasks SET
                text    = COALESCE($3, text),
                subject = CASE WHEN $8 THEN $4 ELSE subject END,
                due     = CASE WHEN $9 THEN $5 ELSE due END,
                kind    = COALESCE($6, kind),
                done    = COALESCE($7, done),
                updated_at = now()
            WHERE id = $2 AND student_id = $1
            RETURNING {TASK_FIELDS}
            """,
            student_id,
            task_id,
            changes.get("text"),
            changes.get("subject"),
            changes.get("due"),
            changes.get("kind"),
            changes.get("done"),
            # subject и due можно осознанно обнулить — COALESCE это не различает,
            # поэтому «поле прислали» передаём отдельным флагом.
            "subject" in changes,
            "due" in changes,
        )

    async def delete_task(self, student_id: UUID, task_id: UUID) -> bool:
        result = await self._db.execute(
            "DELETE FROM tasks WHERE id = $1 AND student_id = $2", task_id, student_id
        )
        return result.endswith("1")

    async def existing_keys(self, student_id: UUID) -> list[asyncpg.Record]:
        return await self._db.fetch(
            "SELECT due, subject, text FROM tasks WHERE student_id = $1", student_id
        )

    async def add_many(self, student_id: UUID, items: list[dict]) -> int:
        """Пакетная вставка импорта — одним заходом, а не по строке за раз."""
        if not items:
            return 0
        async with self._db.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO tasks (student_id, text, subject, due, kind, source)
                VALUES ($1, $2, $3, $4, $5, 'manual')
                """,
                [
                    (student_id, i["text"], i["subject"], i["due"], i["kind"])
                    for i in items
                ],
            )
        return len(items)

    # --- расписание ---

    async def list_classes(self, student_id: UUID) -> list[asyncpg.Record]:
        return await self._db.fetch(
            "SELECT id, day, name, time, room FROM timetable WHERE student_id = $1"
            " ORDER BY day, time",
            student_id,
        )

    async def add_class(
        self, student_id: UUID, day: int, name: str, at, room: str | None
    ) -> asyncpg.Record:
        return await self._db.fetchrow(
            """
            INSERT INTO timetable (student_id, day, name, time, room)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, day, name, time, room
            """,
            student_id,
            day,
            name,
            at,
            room,
        )

    async def delete_class(self, student_id: UUID, class_id: UUID) -> bool:
        result = await self._db.execute(
            "DELETE FROM timetable WHERE id = $1 AND student_id = $2",
            class_id,
            student_id,
        )
        return result.endswith("1")

    async def upsert_moodle_deadlines(
        self, student_id: UUID, items: list[dict]
    ) -> tuple[int, int]:
        """Импорт дедлайнов. Возвращает (добавлено, обновлено).

        Опирается на частичный уникальный индекс (student_id, moodle_event_id):
        повторный импорт не плодит дубли, а перенесённый дедлайн обновляет дату.
        Отметку «сделано» не трогаем — её ставил студент.
        """
        added = updated = 0
        async with self._db.pool.acquire() as conn:
            async with conn.transaction():
                for item in items:
                    if item.get("moodle_event_id") is None:
                        # Без id события отличить повтор не от чего — пропускаем.
                        continue
                    row = await conn.fetchrow(
                        """
                        INSERT INTO tasks
                            (student_id, text, subject, due, kind, source, moodle_event_id)
                        VALUES ($1, $2, $3, $4, $5, 'moodle', $6)
                        ON CONFLICT (student_id, moodle_event_id)
                            WHERE moodle_event_id IS NOT NULL
                        DO UPDATE SET
                            text = EXCLUDED.text,
                            subject = EXCLUDED.subject,
                            due = EXCLUDED.due,
                            updated_at = now()
                        RETURNING (xmax = 0) AS inserted
                        """,
                        student_id,
                        item["text"],
                        item["subject"],
                        item["due"],
                        item["kind"],
                        item["moodle_event_id"],
                    )
                    if row["inserted"]:
                        added += 1
                    else:
                        updated += 1
        return added, updated
