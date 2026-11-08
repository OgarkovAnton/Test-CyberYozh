from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CommentDTO:
    id: str
    author_id: str
    body: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TaskDTO:
    id: str
    title: str
    description: str
    status: str
    creator_id: str
    assignee_id: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    version: int
    comments: tuple[CommentDTO, ...] = ()


def task_to_dto(task) -> TaskDTO:
    return TaskDTO(
        id=str(task.id.value),
        title=task.title.value,
        description=task.description,
        status=task.status.value,
        creator_id=str(task.creator_id.value),
        assignee_id=str(task.assignee_id.value) if task.assignee_id else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        version=task.version,
        comments=tuple(
            CommentDTO(
                id=str(c.id.value),
                author_id=str(c.author_id.value),
                body=c.body.value,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in task.comments
        ),
    )
