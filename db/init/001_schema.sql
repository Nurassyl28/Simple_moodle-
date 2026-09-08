-- Схема SDU Hub. Соответствует SPEC.md §4.
-- Поля для пароля студента здесь нет намеренно (SECURITY.md): пароль
-- используется один раз при обмене на токен и не сохраняется нигде.

CREATE TABLE IF NOT EXISTS students (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    moodle_userid   BIGINT      NOT NULL UNIQUE,
    fullname        TEXT        NOT NULL,
    -- Токен Moodle в зашифрованном виде. Ключ — в переменной окружения
    -- TOKEN_ENCRYPTION_KEY, в БД и в коде его нет.
    token_encrypted BYTEA       NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS sessions_student_idx ON sessions (student_id);
CREATE INDEX IF NOT EXISTS sessions_expires_idx ON sessions (expires_at);

-- Задачи трекера: и домашка (hw), и личные дела (todo).
-- source = 'manual' — добавил студент, 'moodle' — импортировано из дедлайнов.
CREATE TABLE IF NOT EXISTS tasks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    text        TEXT        NOT NULL,
    subject     TEXT,
    due         DATE,
    kind        TEXT        NOT NULL DEFAULT 'hw'     CHECK (kind IN ('hw', 'todo')),
    done        BOOLEAN     NOT NULL DEFAULT FALSE,
    source      TEXT        NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'moodle')),
    -- id события Moodle: чтобы повторный импорт не плодил дубли
    moodle_event_id BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tasks_student_due_idx ON tasks (student_id, due);
CREATE UNIQUE INDEX IF NOT EXISTS tasks_moodle_event_uq
    ON tasks (student_id, moodle_event_id) WHERE moodle_event_id IS NOT NULL;

-- Расписание пар. day — 0=понедельник … 6=воскресенье (как dayIndex в трекере).
CREATE TABLE IF NOT EXISTS timetable (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID        NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    day         SMALLINT    NOT NULL CHECK (day BETWEEN 0 AND 6),
    name        TEXT        NOT NULL,
    time        TIME        NOT NULL,
    room        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS timetable_student_day_idx ON timetable (student_id, day, time);
