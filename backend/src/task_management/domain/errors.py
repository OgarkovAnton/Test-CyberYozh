from __future__ import annotations

from src.shared_kernel.domain.errors import DomainError


class TaskDomainError(DomainError):
    """Base error for the Task Management bounded context."""


class TaskTransitionError(TaskDomainError):
    """Invalid TaskStatus transition."""


class TaskPermissionError(TaskDomainError):
    """Actor is not allowed to perform the requested task operation."""


class TaskNotFoundError(TaskDomainError):
    """Task aggregate could not be found."""


class CommentNotFoundError(TaskDomainError):
    """Raised when a comment id is not present on the task."""


class CommentPermissionError(TaskDomainError):
    """Raised when an actor cannot mutate a comment they do not own."""


class AssigneeNotFoundError(TaskDomainError):
    """Assignee id does not refer to an active user."""

    def __init__(self) -> None:
        super().__init__("Assignee does not exist or is inactive", code="AssigneeNotFound")


class TaskConflictError(TaskDomainError):
    """Persisted task version does not match the loaded aggregate."""

    def __init__(self) -> None:
        super().__init__("Task was modified by someone else", code="TaskConflict")


class InvalidTaskStatusError(TaskDomainError):
    """Query status is not a known TaskStatus value."""

    def __init__(self, status: str) -> None:
        super().__init__(f"Unknown task status {status!r}", code="InvalidTaskStatus")
