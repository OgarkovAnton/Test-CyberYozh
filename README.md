# Task Management

Веб-трекер задач: общая доска, роли создателя, исполнителя и PM, комментарии и уведомления. Как устроены контексты, слои и доставка событий — в [ARCHITECTURE.md](ARCHITECTURE.md). Схема ручек — в Swagger.

## Запуск

```bash
cp .env.example .env
```

В `.env` задайте свой `DJANGO_SECRET_KEY`. Значение из примера — заглушка.

```bash
docker compose up --build
```

Зависимости ставятся в образ, поэтому нужен `--build`. В отдельном терминале:

```bash
make migrate
make seed
```

| Куда | Адрес |
|------|--------|
| Интерфейс | http://localhost:5173/ |
| API | http://localhost:8000/api/v1/ |
| Swagger | http://localhost:8000/api/docs/ |
| Схема OpenAPI | http://localhost:8000/api/schema/ |
| Проверка живости | http://localhost:8000/health/ |

Локально, без контейнера `web`:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
python manage.py runserver
```

Postgres и Redis при этом уже запущены, а `POSTGRES_*` и `REDIS_URL` указывают на них.

## Общая информация

Демо-пользователи: `alice@example.com` (admin, `is_staff`) и `bob@example.com`, пароль `password123`. `make seed` не перезаписывает пароли уже созданных учёток и не дублирует демо-задачу. Если Alice уже есть без флага, повторный запуск ставит ей `is_staff`. Регистрация этот флаг не выдаёт.

Любой вошедший пользователь видит все задачи. Текст, назначение, статусы и удаление зависят от роли и текущего статуса. Комментарий может оставить любой вошедший, правит и удаляет его автор.

Стек: Django 5, DRF, SimpleJWT, drf-spectacular, PostgreSQL 16, Redis 7, Celery, React, TypeScript, Vite, TanStack Query. В Compose сервисы `web`, `worker`, `beat`, `db`, `redis`, `frontend`.

Тесты:

```bash
make test-domain
make test
```

`make test` использует `config.settings.test`: SQLite в памяти, задачи Celery выполняются сразу. То же локально:

```bash
cd backend
PYTHONPATH=. pytest -q
```
