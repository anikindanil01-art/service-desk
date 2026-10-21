# Сервис заявок

Программный модуль учёта заявок (Service Desk) с REST API, базой данных, миграциями и тестами.
Выполнено в рамках производственной практики.

## Возможности

- CRUD заявок: создание, список с фильтрами (статус, приоритет, исполнитель) и постраничной навигацией, получение по id, редактирование, мягкое удаление (`is_deleted`)
- Жизненный цикл заявки `NEW → IN_PROGRESS → RESOLVED → CLOSED`, недопустимые переходы запрещены
- Пользователи с ролями `USER`, `EXECUTOR`, `ADMIN`, назначение исполнителя
- Комментарии к заявке
- JWT-аутентификация и разграничение прав (например, удалять заявки может только `ADMIN`)
- Документация Swagger/OpenAPI

## Стек

| Компонент | Что используется |
|---|---|
| Язык | Python 3.12 |
| Веб-фреймворк | Flask |
| База данных | SQLite (модуль `sqlite3`) |
| Миграции | SQL-файлы в `migrations/` и запускатель `app/migrate.py` |
| JWT | PyJWT |
| Тесты | `unittest` (тесты также запускаются через `pytest`) |
| Документация API | OpenAPI 3.0, Swagger UI на `/docs` |

## Структура проекта

```
app/
  api/            контроллеры (Flask blueprints)
  services/       бизнес-логика
  repositories/   доступ к БД
  security.py     JWT и хеширование паролей
  openapi.py      описание API
  migrate.py      запуск миграций
migrations/       SQL-миграции
tests/            модульные и интеграционные тесты
docs/             design.md, openapi.json, coverage_report.html
tools/            скрипт измерения покрытия
```

## Запуск

```bash
# 1. Виртуальное окружение и зависимости
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Применить миграции (создаётся файл service_desk.db)
python -m app.migrate

# 3. Запустить сервер
python run.py
```

Сервис будет доступен на `http://127.0.0.1:5000`, Swagger UI открывается на `http://127.0.0.1:5000/docs`, спецификация на `/openapi.json` (копия лежит в `docs/openapi.json`).

Настройки через переменные окружения: `DATABASE` (путь к файлу БД), `SECRET_KEY` (ключ подписи JWT), `JWT_EXPIRES_MINUTES` (срок жизни токена, по умолчанию 60).

## Примеры запросов

```bash
# Регистрация (роль можно передать при регистрации: USER, EXECUTOR, ADMIN)
curl -X POST http://127.0.0.1:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "ivan", "password": "secret1", "role": "USER"}'

# Вход, в ответе access_token
curl -X POST http://127.0.0.1:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ivan", "password": "secret1"}'

# Создание заявки
curl -X POST http://127.0.0.1:5000/tickets \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"subject": "Не работает принтер", "description": "3 этаж", "priority": "HIGH"}'

# Список заявок с фильтрами и страницами
curl "http://127.0.0.1:5000/tickets?status=NEW&priority=HIGH&page=1&page_size=10" \
  -H "Authorization: Bearer <token>"

# Назначить исполнителя (только ADMIN)
curl -X PATCH http://127.0.0.1:5000/tickets/1/assignee \
  -H "Authorization: Bearer <admin_token>" -H "Content-Type: application/json" \
  -d '{"assignee_id": 2}'

# Сменить статус (исполнитель заявки или ADMIN)
curl -X PATCH http://127.0.0.1:5000/tickets/1/status \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"status": "IN_PROGRESS"}'

# Добавить комментарий
curl -X POST http://127.0.0.1:5000/tickets/1/comments \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"text": "Начал диагностику"}'

# Мягкое удаление (только ADMIN)
curl -X DELETE http://127.0.0.1:5000/tickets/1 -H "Authorization: Bearer <admin_token>"
```

## Тесты и покрытие

```bash
# Запуск всех тестов (модульные и интеграционные)
python -m unittest discover -v

# Покрытие по строкам, отчёт сохраняется в docs/coverage_report.html
python tools/coverage_report.py
```

Если установлен `pytest-cov`, то можно использовать и его: `pytest --cov=app/services tests/`.

## Документация

- `docs/design.md` — проектирование (Use Case, ER-диаграмма, архитектура, статусы, права, эндпоинты)
- `docs/openapi.json` — спецификация OpenAPI
- `docs/coverage_report.html` — отчёт о покрытии тестами
