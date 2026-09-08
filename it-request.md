# Обращение в IT-отдел SDU — шаблон

Отправить до запуска сервиса на реальных студентах. Цель — получить явное разрешение
и, в идеале, официальный доступ к Moodle Web Services.

---

## Русский

Тема: Разрешение на студенческий проект поверх Moodle (Mobile API)

Здравствуйте!

Меня зовут Нурасыл Базарбай, студент программы Computer Science (2026).
Я разрабатываю учебный проект — удобный интерфейс, который показывает студенту его
собственные курсы, оценки и дедлайны из Moodle в одном месте, особенно на телефоне.

Технически я планирую использовать тот же механизм, что и официальное мобильное
приложение Moodle (Mobile Web Services, service=moodle_mobile_app): студент сам входит
своим логином, сервис получает токен и показывает данные только этого студента.
Пароли не сохраняются, каждый видит только свои данные.

Прошу подсказать:
1. Допустимо ли создание такого сервиса для студентов SDU?
2. Есть ли возможность получить официальный доступ к Web Services (отдельная учётная
   запись/сервис-токен), чтобы не зависеть от пользовательских токенов?
3. Какие требования по безопасности и хранению данных вы предъявляете?

Готов показать текущий прототип и обсудить детали. Спасибо!

---

## English

Subject: Permission for a student project on top of Moodle (Mobile API)

Hello,

My name is Nurassyl Bazarbay, a Computer Science student (2026). I'm building a student
project — a convenient interface that shows a student their own courses, grades and
deadlines from Moodle in one place, especially on mobile.

Technically I plan to use the same mechanism as the official Moodle mobile app
(Mobile Web Services, service=moodle_mobile_app): the student logs in with their own
credentials, the service obtains a token and shows only that student's data. Passwords
are never stored; each user sees only their own data.

Could you advise:
1. Is building such a service for SDU students acceptable?
2. Is it possible to get official Web Services access (a dedicated account / service
   token) so it doesn't rely on per-user tokens?
3. What security and data-handling requirements do you have?

I'm happy to demo the current prototype and discuss details. Thank you!
