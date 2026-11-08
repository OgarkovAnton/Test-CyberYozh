from __future__ import annotations

import logging

from django.db import transaction

from src.shared_kernel.domain.aggregate import AggregateRoot
from src.shared_kernel.domain.ports import OutboxPort, UnitOfWorkPort
from src.shared_kernel.infrastructure.outbox import DjangoOutbox
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.repositories import TaskRepository
from src.task_management.infrastructure.persistence.repositories import DjangoTaskRepository

logger = logging.getLogger(__name__)


def _schedule_outbox_relay() -> None:
    from src.notifications.tasks import relay_outbox

    def _enqueue() -> None:
        try:
            relay_outbox.delay()
        except Exception:
            logger.exception("Failed to enqueue outbox relay")

    transaction.on_commit(_enqueue)


class DjangoUnitOfWork(UnitOfWorkPort):
    """Atomic persistence of Task aggregate changes + outbox events."""

    def __init__(
        self,
        *,
        tasks: TaskRepository | None = None,
        outbox: OutboxPort | None = None,
    ) -> None:
        self.tasks = tasks or DjangoTaskRepository()
        self._outbox = outbox or DjangoOutbox()
        self._atomic = None
        self._pending: list[tuple[str, AggregateRoot]] = []

    def __enter__(self) -> DjangoUnitOfWork:
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self._pending = []
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._atomic is not None
        if exc_type is not None:
            self.rollback()
        self._atomic.__exit__(exc_type, exc, tb)
        self._atomic = None

    @property
    def outbox(self) -> OutboxPort:
        return self._outbox

    def register_new(self, task: Task) -> None:
        self._pending.append(("add", task))

    def register_dirty(self, task: Task) -> None:
        self._pending.append(("save", task))

    def register_removed(self, task: Task) -> None:
        self._pending.append(("remove", task))

    def commit(self) -> None:
        events = []
        for action, aggregate in self._pending:
            if action == "add":
                self.tasks.add(aggregate)  # type: ignore[arg-type]
            elif action == "save":
                self.tasks.save(aggregate)  # type: ignore[arg-type]
            elif action == "remove":
                self.tasks.remove(aggregate)  # type: ignore[arg-type]
            events.extend(aggregate.pull_events())
        if events:
            self._outbox.enqueue(events)
            _schedule_outbox_relay()
        self._pending = []

    def rollback(self) -> None:
        self._pending = []
