# Архитектура

Modular monolith на Django: три bounded context в одном процессе. Строгий DDD только в core subdomain — TaskManagement. Identity и Notifications тоньше: там нет богатой domain model, потому что инварианты сосредоточены в задаче.

```text
Identity --UserId--> TaskManagement --domain event--> Outbox --worker--> Notifications
```

## Context map

| Bounded context | Тип | Ответственность |
|-----------------|-----|-----------------|
| Identity | supporting | Учётная запись, login по email, JWT |
| TaskManagement | core | Aggregate задачи, комментарии, инварианты |
| Notifications | generic | Доставка domain event до inbox |
| `shared_kernel` | — | `AggregateRoot`, `DomainEvent`, `UserId`, ports |

Identity наружу отдаёт `UserId`. TaskManagement зависит от идентификатора, не от Django `User`: существование и активность assignee проверяет application layer до вызова domain. Notifications читает payload события и не загружает aggregate повторно.

Admin — это `User.is_staff`. Presentation кладёт флаг в `ActorContext`. Дальше policy видит actor, а не ORM-пользователя.

## Layers

```text
presentation (DRF, React)
    → application (commands, queries)
        → domain (aggregate, policy, domain event)
    ← infrastructure (ORM, outbox, Celery, Redis)
```

Dependency rule: `domain` импортирует только `shared_kernel` и свои типы. `infrastructure` реализует ports: repository, Unit of Work, outbox. Presentation собирает command или query и переводит domain error в HTTP.

## Domain model

Корень aggregate — `Task`. `Comment` — entity внутри consistency boundary: комментарий сохраняется вместе с задачей.

Value objects: `TaskId`, `UserId`, `CommentId`, `TaskTitle`, `CommentBody`, `TaskStatus`. Состояние меняют методы aggregate: `create`, `change_details`, `assign`, `start_progress`, `return_to_todo`, `complete`, `reopen`, `add_comment`, `edit_comment`, `remove_comment`.

Инварианты и authorization держат policy, а не набор DRF permission:

- `TaskStatusPolicy` — state machine и обязательный assignee на старте.
- `TaskAccessPolicy` — кто из actor (creator, assignee, admin) выполняет операцию в текущем статусе.
- `CommentPolicy` — комментарий доступен любому authenticated пользователю; edit и delete — у автора.

State machine: `todo → in_progress → done`, возврат `in_progress → todo`, reopen `done → todo`. Возврат и reopen сохраняют assignee.

## Application

CQRS-lite. Command загружает aggregate, вызывает метод и коммитит Unit of Work. Query читает ORM projection и в mutator не заходит.

Один Unit of Work — одна DB transaction на aggregate и строки outbox. Регистрация: new, dirty, removed. После записи `pull_events()` складывает domain event в outbox.

Optimistic concurrency: у aggregate есть `version`. `PUT` присылает версию, которую прочитал клиент. Расхождение — `409` `TaskConflict` до записи. Repository дополнительно делает compare-and-swap: `UPDATE ... WHERE version = loaded`. Так перекрывающиеся commit не теряют комментарии.

List query — отдельная projection: фильтр по queryset, страница 20 через `LIMIT`/`OFFSET`, без коллекции комментариев. Карточка грузит aggregate целиком.

## Transactional outbox

Use case фиксирует aggregate и `OutboxMessage` в одной transaction. `transaction.on_commit` ставит Celery task `notifications.relay_outbox`. Ошибка брокера пишется в лог и не откатывает уже зафиксированную задачу. Beat раз в 10 секунд запускает тот же relay. После 5 неудачных попыток сообщение уходит в dead letter. Выборка берёт строку с `skip_locked`, если это умеет СУБД.

Domain Celery не вызывает: доставка — забота infrastructure.

Handler создаёт notification на `TaskAssigned` и `CommentAdded`. Idempotency — `get_or_create` по `(event_id, recipient)`. Actor не получает notification о своём действии. Новая строка публикуется в Redis channel получателя.

Inbox читается `GET /notifications/me/` — это source of truth. `GET /notifications/stream/` — SSE (`text/event-stream`): кадр `notification` с `id`, `event_type`, `created_at`, keep-alive раз в 15 секунд. Поток сообщает, что notification уже записана.

## API

Префикс `/api/v1/`. Аутентификация — JWT Bearer: access 30 минут, refresh 7 дней. OpenAPI собирает drf-spectacular; `/api/schema/` и `/api/docs/` открыты без токена.

Domain error уходит телом `{ "detail": "...", "code": "..." }`. Нарушение инварианта — 400, запрещённая операция — 403, отсутствующая сущность — 404, конфликт версии или недопустимый переход — 409.

## Frontend

React, TypeScript, feature folders `auth` и `tasks`. Своего domain layer на клиенте нет: API client и TanStack Query. Axios подставляет access token и один раз обновляет его через refresh.

Форма карточки хранит draft и в `PUT` отправляет `version`, снятую при загрузке этого draft. `409` сбрасывает draft и инвалидирует query задачи. SSE открывается через `fetch` с заголовком `Authorization`; кадр инвалидирует query inbox.

## Runtime

Compose: `web`, `worker`, `beat`, `db` (PostgreSQL 16), `redis` (Redis 7), `frontend` (Vite). `web` принимает HTTP и пишет в Postgres. `worker` разбирает outbox. `beat` страхует relay по расписанию. Redis — брокер Celery и канал SSE.
