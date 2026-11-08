from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_status import TaskStatus


class TaskRepository(ABC):
    """Persistence port for the Task aggregate root only."""

    @abstractmethod
    def get(self, task_id: TaskId) -> Task | None:
        ...

    @abstractmethod
    def add(self, task: Task) -> None:
        ...

    @abstractmethod
    def save(self, task: Task) -> None:
        ...

    @abstractmethod
    def remove(self, task: Task) -> None:
        ...


class TaskQueryRepository(ABC):
    """Read-side port (CQRS-lite) — may bypass aggregate mutation API."""

    @abstractmethod
    def list_tasks(
        self,
        *,
        viewer_id: UserId,
        is_staff: bool = False,
        status: TaskStatus | None = None,
        assignee_id: UserId | None = None,
        creator_id: UserId | None = None,
        search: str | None = None,
    ) -> list[Task]:
        ...

    @abstractmethod
    def get_for_viewer(
        self,
        task_id: TaskId,
        *,
        viewer_id: UserId,
        is_staff: bool = False,
    ) -> Task | None:
        ...


# Convenience alias used by some adapters
TaskIdRaw = UUID
