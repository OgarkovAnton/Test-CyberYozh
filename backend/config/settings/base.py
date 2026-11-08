from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Ensure `src.*` packages are importable when PYTHONPATH is not set externally.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "dev-only-insecure-secret-key-min-32-bytes",
)
DEBUG = os.getenv("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    # Bounded contexts
    "src.shared_kernel.apps.SharedKernelConfig",
    "src.identity.apps.IdentityConfig",
    "src.task_management.apps.TaskManagementConfig",
    "src.notifications.apps.NotificationsConfig",
]

AUTH_USER_MODEL = "identity.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "task_management"),
        "USER": os.getenv("POSTGRES_USER", "task_user"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "task_password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": (
        "src.shared_kernel.infrastructure.exception_handler.domain_exception_handler"
    ),
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Task Management API",
    "DESCRIPTION": """
Трекер задач. Все ручки, кроме регистрации, логина, refresh и Swagger, требуют
`Authorization: Bearer <access>`.

Жизненный цикл: `todo → in_progress → done`. Возврат `in_progress → todo`
оставляет исполнителя. Переоткрытие `done → todo` тоже. Завершить можно только
из `in_progress`. Старт требует назначенного исполнителя. Менять исполнителя
можно только в `todo` через `POST /tasks/{id}/assign/` (`assignee_id: null`
снимает его). `PUT` меняет только заголовок и описание.

Роли: создатель, текущий исполнитель и PM (`is_staff`). Любой вошедший видит
все задачи и может комментировать. Чужой комментарий правит и удаляет только
автор.

Каждая задача отдаёт `version`. `PUT` обязан прислать версию последнего чтения.
Если с тех пор задачу изменили, ответ `409` и код `TaskConflict`.

Уведомления пишутся из transactional outbox. `GET /notifications/stream/` —
SSE: кадр `event: notification` после записи уведомления этому пользователю.
Список `GET /notifications/me/` остаётся источником правды.

Ошибки домена: `{ "detail": "...", "code": "..." }`. 400 — правило или
валидация, 403 — нет права, 404 — нет объекта, 409 — конфликт версии или
недопустимый переход статуса.
    """.strip(),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "Auth", "description": "Регистрация и JWT."},
        {"name": "Users", "description": "Текущий пользователь и список для назначения."},
        {"name": "Tasks", "description": "Доска, карточка и переходы статуса."},
        {"name": "Comments", "description": "Комментарии внутри агрегата задачи."},
        {"name": "Notifications", "description": "Ящик и SSE-поток."},
    ],
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "relay-outbox": {
        "task": "notifications.relay_outbox",
        "schedule": 10.0,
    },
}
