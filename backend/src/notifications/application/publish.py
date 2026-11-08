from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from redis import Redis

logger = logging.getLogger(__name__)


def channel_name(recipient_id: str) -> str:
    return f"notifications:{recipient_id}"


def publish_notification(recipient_id: str, message: dict[str, Any]) -> None:
    """Best-effort push. The inbox GET stays the source of truth if Redis is down."""
    try:
        client = Redis.from_url(settings.REDIS_URL)
        client.publish(channel_name(recipient_id), json.dumps(message))
    except Exception:
        logger.exception("Failed to publish notification for %s", recipient_id)
