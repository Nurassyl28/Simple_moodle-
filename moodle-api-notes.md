# Moodle API — проверенные заметки

Всё ниже проверено против `https://moodle.sdu.edu.kz` (Moodle 2024100711.04),
реальными запросами, ответ `200`. Токен в примерах заменён на `TOKEN`.

## Базовый вид вызова

```
GET https://moodle.sdu.edu.kz/webservice/rest/server.php
    ?wstoken=TOKEN
    &wsfunction={FUNCTION}
    &moodlewsrestformat=json
    &{extra params}
```

Ответ — JSON. Ошибка выглядит так (всегда проверять наличие `exception`):
```json
{ "exception": "...", "errorcode": "invalidtoken", "message": "..." }
```
Частые `errorcode`:
- `invalidtoken` — токен сброшен/неверен, получить новый.
- `accessexception` — функция есть, но нет прав (у SDU не встречалось на проверенных fn).

## Обмен логина на токен

```
GET https://moodle.sdu.edu.kz/login/token.php?username=U&password=P&service=moodle_mobile_app
→ { "token":"...", "privatetoken":"..." }
```

## Проверенные функции

1. `core_webservice_get_site_info` — профиль, `userid`, `fullname`, `userpictureurl`.
2. `core_enrol_get_users_courses` + `userid` — список курсов.
3. `gradereport_user_get_grade_items` + `courseid` + `userid` — оценки.
   Путь к данным: `usergrades[0].gradeitems[]`, показывать `gradeformatted`.
4. `core_course_get_contents` + `courseid` — секции → modules → contents (файлы).
   Файл: `fileurl` + `?token=TOKEN` (или `&token=` если уже есть `?`).
5. `core_calendar_get_action_events_by_timesort` + `timesortfrom` — дедлайны.
   `events[].timesort` — unix-время.

## Наблюдение по объёму данных (08.09.2026, начало семестра)

Тестовый аккаунт вернул: 1 курс, 1 «итог по курсу» без оценки (`-`), 5 файлов, 0 дедлайнов.
Это отражает пустой на старте семестр, не предел API. Ожидать наполнения позже.

## CORS

Прямой fetch из страницы-файла в Moodle блокируется (`Failed to fetch`).
Прототип обходит локальным Python-посредником:

```
cd ~/Downloads && python3 -c "from http.server import*;from urllib.request import urlopen,Request;from urllib.parse import urlparse,parse_qs;
class H(SimpleHTTPRequestHandler):
 def do_GET(s):
  if s.path.startswith('/proxy?'):
   url=parse_qs(urlparse(s.path).query)['u'][0]
   try:
    d=urlopen(Request(url,headers={'User-Agent':'m'})).read()
    s.send_response(200);s.send_header('Access-Control-Allow-Origin','*');s.end_headers();s.wfile.write(d)
   except Exception as e:
    s.send_response(500);s.end_headers();s.wfile.write(str(e).encode())
  else:SimpleHTTPRequestHandler.do_GET(s)
HTTPServer(('127.0.0.1',8765),H).serve_forever()"
```

В продакшене посредник не нужен — его роль выполняет бэкенд.
