from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.shared_kernel.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskCreated(DomainEvent):
    title: str
    description: str
    creator_id: UUID
    assignee_id: UUID | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskDetailsChanged(DomainEvent):
    title: str
    description: str


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskAssigned(DomainEvent):
    assignee_id: UUID | None
    previous_assignee_id: UUID | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskProgressStarted(DomainEvent):
    started_by: UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskReturnedToTodo(DomainEvent):
    returned_by: UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskCompleted(DomainEvent):
    completed_by: UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class TaskReopened(DomainEvent):
    reopened_by: UUID


@dataclass(frozen=True, kw_only=True, slots=True)
class CommentAdded(DomainEvent):
    comment_id: UUID
    author_id: UUID
    body: str
    creator_id: UUID
    assignee_id: UUID | None = None


@dataclass(frozen=True, kw_only=True, slots=True)
class CommentEdited(DomainEvent):
    comment_id: UUID
    editor_id: UUID
    body: str


@dataclass(frozen=True, kw_only=True, slots=True)
class CommentRemoved(DomainEvent):
    comment_id: UUID
    removed_by: UUID
