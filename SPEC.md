# SPEC — SDU Hub

Техническая спецификация. Пиши бэкенд по ней. Все обращения к Moodle — только с бэкенда.

## 0. Термины

- **site** — базовый адрес Moodle, `https://moodle.sdu.edu.kz`.
- **token** — Moodle mobile token студента. Секрет. Хранится зашифрованным.
- **REST-вызов Moodle**:
  `GET {site}/webservice/rest/server.php?wstoken={token}&wsfunction={fn}&moodlewsrestformat=json&{params}`
  Ошибка приходит как JSON с полем `exception` и `errorcode` — всегда проверять.

## 1. Получение токена (обмен логина)

```
GET {site}/login/token.php?username={u}&password={p}&service=moodle_mobile_app
→ 200 { "token": "...", "privatetoken": "..." }
→ или { "error": "Invalid login, please try again" }
```

Правила:
- Вызывается только бэкендом, по HTTPS.
- `username`/`password` приходят от студента, используются один раз, **не логируются,
  не сохраняются ни в каком виде**.
- Хранится только `token` (зашифрованным). `privatetoken` не нужен — не хранить.

## 2. Данные студента (проверенные функции)

### 2.1 Профиль / userid
```
fn = core_webservice_get_site_info
→ { userid, fullname, sitename, userpictureurl, ... }
```
`userid` нужен для последующих вызовов. `userpictureurl` требует `?token=` для загрузки.

### 2.2 Курсы
```
fn = core_enrol_get_users_courses
params: userid={userid}
→ [ { id, fullname, shortname, ... }, ... ]
```

### 2.3 Оценки по курсу
```
fn = gradereport_user_get_grade_items
params: courseid={courseId}&userid={userid}
→ { usergrades: [ { gradeitems: [ { itemname, itemtype, gradeformatted, grademin, grademax }, ... ] } ] }
```
- `itemtype === "course"` — итоговая оценка за курс.
- `gradeformatted` — то, что показывать; `"-"` значит оценки ещё нет.
- Перебирать по всем курсам из 2.2.

### 2.4 Содержимое курса (файлы, ресурсы)
```
fn = core_course_get_contents
params: courseid={courseId}
→ [ { name(section), modules: [ { name, modname, contents: [ { filename, fileurl, mimetype, timemodified }, ... ] } ] } ]
```
- Файл качается по `fileurl` + `?token={token}` (или `&token=` если в url уже есть `?`).
- `fileurl` может быть пустым у модулей без файлов — пропускать.

### 2.5 Ближайшие дедлайны
```
fn = core_calendar_get_action_events_by_timesort
params: timesortfrom={unixNow}
→ { events: [ { name, timesort, course: { shortname } }, ... ] }
```
- `timesort` — unix-время дедлайна.
- Пусто в начале семестра — это норма.

## 3. Эндпоинты бэкенда (что отдаём фронту)

Фронт НИКОГДА не видит токен. Только чистый JSON ниже.

```
POST /api/login        { username, password } → { sessionId }        // обмен на токен, токен шифруется и кладётся в БД
GET  /api/me           → { fullname, avatar, courses: [...] }
GET  /api/grades       → [ { course, item, grade, range } ]
GET  /api/files        → [ { course, name, downloadUrl } ]           // downloadUrl проксируется через бэкенд, без токена в ссылке
GET  /api/deadlines    → [ { date, course, name } ]
POST /api/logout       → удаляет сессию и токен
```

Трекер (собственные данные студента, не из Moodle):
```
GET/POST/PATCH/DELETE /api/tasks   { text, subject, due, kind: "hw"|"todo", done }
GET/POST/DELETE       /api/timetable
```

## 4. Модель данных (минимум)

```
students   ( id, moodle_userid, fullname, token_encrypted, created_at )
sessions   ( id, student_id, expires_at )
tasks      ( id, student_id, text, subject, due, kind, done, source )   // source: "manual" | "moodle"
timetable  ( id, student_id, day, name, time, room )
```

Пароль студента в модели **отсутствует намеренно** — его нельзя хранить.

## 5. Правила показа (из готового трекера)

Логика группировки задач (Просрочено / Сегодня / Завтра / Дальше / Без даты / Сделано),
подсказка «следующая пара по предмету» и импорт строк `дата | предмет | задание`
уже реализованы в `legacy/homework-tracker.jsx` — переиспользовать, не писать заново.

## 6. Чего НЕ делать

- Не ходить в Moodle с фронтенда.
- Не класть токен в URL, в ссылки на файлы, отдаваемые фронту, в логи.
- Не хранить пароли. Никогда. Ни «временно», ни «в зашифрованном виде».
- Не запускать публичный сервис до разрешения SDU (см. SECURITY.md, README Фаза 1).
