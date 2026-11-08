from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from redis import Redis
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.views import APIView

from src.notifications.application.publish import channel_name

logger = logging.getLogger(__name__)


def iter_redis_messages(user_id: str) -> Iterator[dict[str, Any] | None]:
    client = Redis.from_url(settings.REDIS_URL)
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel_name(user_id))
    try:
        while True:
            message = pubsub.get_message(timeout=15)
            if message is None:
                yield None
                continue
            if message.get("type") != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()
            yield json.loads(data)
    finally:
        pubsub.close()
        client.close()


def iter_sse(user_id: str) -> Iterator[str]:
    yield ": connected\n\n"
    try:
        for item in iter_redis_messages(str(user_id)):
            if item is None:
                yield ": keep-alive\n\n"
                continue
            payload = json.dumps(item, separators=(",", ":"))
            yield f"event: notification\ndata: {payload}\n\n"
    except Exception:
        logger.exception("Notification stream failed for %s", user_id)
        yield 'event: error\ndata: {"detail":"stream unavailable"}\n\n'


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "txt"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class NotificationStreamView(APIView):
    renderer_classes = [EventStreamRenderer, JSONRenderer]

    @extend_schema(
        tags=["Notifications"],
        summary="Поток уведомлений (SSE)",
        description=(
            "Держит соединение `text/event-stream`. Кадр `event: notification` "
            "приходит после того, как outbox записал уведомление этому пользователю. "
            "Тело кадра: id, event_type, created_at. Каждые 15 секунд без событий "
            "уходит комментарий `: keep-alive`. Браузерный EventSource заголовок "
            "Authorization не ставит, поэтому клиент читает поток через fetch. "
            "После обрыва список нужно догнать через GET /notifications/me/."
        ),
        responses={200: {"description": "text/event-stream"}},
    )
    def get(self, request):
        response = StreamingHttpResponse(
            iter_sse(request.user.id),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
