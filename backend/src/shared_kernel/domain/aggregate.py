from __future__ import annotations

from src.shared_kernel.domain.events import DomainEvent


class AggregateRoot:
    """Base aggregate root with an internal domain-event buffer."""

    def __init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def _record(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Return and clear recorded domain events (for UoW / outbox)."""
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    @property
    def pending_events(self) -> tuple[DomainEvent, ...]:
        return tuple(self._domain_events)
