from __future__ import annotations

import logging

from celery import shared_task
from django.db import connection, transaction
from django.utils import timezone

from src.notifications.application.handlers import handle_domain_event
from src.shared_kernel.infrastructure.models import OutboxMessage

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


@shared_task(name="notifications.relay_outbox")
def relay_outbox(batch_size: int = 50) -> int:
    """Publish unpublished outbox messages to notification handlers."""
    skip_locked = bool(getattr(connection.features, "has_select_for_update_skip_locked", False))
    processed = 0
    with transaction.atomic():
        messages = list(
            OutboxMessage.objects.select_for_update(skip_locked=skip_locked)
            .filter(processed_at__isnull=True, dead_lettered_at__isnull=True)
            .order_by("created_at")[:batch_size]
        )
        for message in messages:
            try:
                handle_domain_event(message.payload)
            except Exception:
                logger.exception("Failed to process outbox message %s", message.event_id)
                message.attempts += 1
                if message.attempts >= MAX_ATTEMPTS:
                    message.dead_lettered_at = timezone.now()
                message.save(update_fields=["attempts", "dead_lettered_at"])
                continue
            message.processed_at = timezone.now()
            message.save(update_fields=["processed_at"])
            processed += 1
    return processed


@shared_task(name="notifications.dispatch_event")
def dispatch_event(payload: dict) -> None:
    handle_domain_event(payload)
