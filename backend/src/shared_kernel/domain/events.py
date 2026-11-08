from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True, slots=True)
class DomainEvent:
    """Base class for domain events raised by aggregates."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    aggregate_id: UUID | None = None
    aggregate_type: str | None = None
    actor_id: UUID | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict[str, Any]:
        # slots=True dataclasses have no __dict__; use dataclass fields instead.
        payload: dict[str, Any] = {}
        for event_field in fields(self):
            value = getattr(self, event_field.name)
            if isinstance(value, UUID):
                payload[event_field.name] = str(value)
            elif isinstance(value, datetime):
                payload[event_field.name] = value.isoformat()
            else:
                payload[event_field.name] = value
        payload["event_type"] = self.event_type
        return payload
