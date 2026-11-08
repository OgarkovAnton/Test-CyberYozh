from __future__ import annotations

from config.settings.base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key-must-be-at-least-32-bytes-long"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
