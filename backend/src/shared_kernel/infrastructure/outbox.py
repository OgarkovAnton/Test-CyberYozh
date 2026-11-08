from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from django.utils import timezone

from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.domain.ports import OutboxPort
from src.shared_kernel.infrastructure.models import OutboxMessage


class DjangoOutbox(OutboxPort):
    def enqueue(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            OutboxMessage.objects.create(
                event_id=event.event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type or "",
                aggregate_id=event.aggregate_id,
                payload=event.to_dict(),
            )

    def mark_published(self, event_ids: Sequence[Any]) -> None:
        ids = [UUID(str(event_id)) for event_id in event_ids]
        OutboxMessage.objects.filter(event_id__in=ids, processed_at__isnull=True).update(
            processed_at=timezone.now()
        )
