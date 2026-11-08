from __future__ import annotations

from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from redis import Redis
from redis.exceptions import RedisError
from rest_framework.permissions import AllowAny


def healthcheck(_request):
    checks: dict[str, str] = {}
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"

    try:
        from django.conf import settings

        Redis.from_url(settings.REDIS_URL).ping()
        checks["redis"] = "ok"
    except (RedisError, OSError):
        checks["redis"] = "error"

    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JsonResponse(
        {"status": "ok" if status_code == 200 else "degraded", "checks": checks},
        status=status_code,
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
    path(
        "api/schema/",
        SpectacularAPIView.as_view(authentication_classes=[], permission_classes=[AllowAny]),
        name="schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(
            url_name="schema",
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name="swagger-ui",
    ),
    path("api/v1/", include("src.identity.presentation.urls")),
    path("api/v1/", include("src.task_management.presentation.urls")),
    path("api/v1/", include("src.notifications.presentation.urls")),
]
