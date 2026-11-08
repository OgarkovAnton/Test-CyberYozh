from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from src.shared_kernel.domain.events import DomainEvent


class OutboxPort(ABC):
    """Port for transactional outbox persistence of domain events."""

    @abstractmethod
    def enqueue(self, events: Sequence[DomainEvent]) -> None:
        """Persist events so they can be published asynchronously."""

    @abstractmethod
    def mark_published(self, event_ids: Sequence[Any]) -> None:
        """Mark previously enqueued events as published."""


class UnitOfWorkPort(ABC):
    """Port for atomic commit of aggregate changes + outbox writes."""

    @abstractmethod
    def __enter__(self) -> UnitOfWorkPort:
        ...

    @abstractmethod
    def __exit__(self, exc_type, exc, tb) -> None:
        ...

    @property
    @abstractmethod
    def outbox(self) -> OutboxPort:
        ...

    @abstractmethod
    def commit(self) -> None:
        """Persist all tracked changes atomically."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard pending changes."""
