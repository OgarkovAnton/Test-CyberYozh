from __future__ import annotations

from dataclasses import dataclass

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.application.dto import TaskDTO, task_to_dto
from src.task_management.domain.errors import InvalidTaskStatusError, TaskNotFoundError
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_status import TaskStatus
from src.task_management.infrastructure.persistence.repositories import (
    DjangoTaskQueryRepository,
)


@dataclass(frozen=True, slots=True)
class ListTasksQuery:
    actor: ActorContext
    status: str | None = None
    assignee_id: str | None = None
    creator_id: str | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class GetTaskQuery:
    task_id: str
    actor: ActorContext


class ListTasksQueryService:
    def __init__(self, repo: DjangoTaskQueryRepository | None = None) -> None:
        self._repo = repo or DjangoTaskQueryRepository()

    def queryset(self, query: ListTasksQuery):
        status = None
        if query.status:
            try:
                status = TaskStatus(query.status)
            except ValueError as exc:
                raise InvalidTaskStatusError(query.status) from exc
        return self._repo.filtered_tasks(
            status=status,
            assignee_id=UserId.from_str(query.assignee_id) if query.assignee_id else None,
            creator_id=UserId.from_str(query.creator_id) if query.creator_id else None,
            search=query.search,
        )


class GetTaskQueryService:
    def __init__(self, repo: DjangoTaskQueryRepository | None = None) -> None:
        self._repo = repo or DjangoTaskQueryRepository()

    def execute(self, query: GetTaskQuery) -> TaskDTO:
        task = self._repo.get_for_viewer(
            TaskId.from_str(query.task_id),
            viewer_id=query.actor.user_id,
            is_staff=query.actor.is_staff,
        )
        if task is None:
            raise TaskNotFoundError(f"Task {query.task_id} not found")
        return task_to_dto(task)
