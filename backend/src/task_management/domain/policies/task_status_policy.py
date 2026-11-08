from __future__ import annotations

from src.task_management.domain.errors import TaskDomainError, TaskTransitionError
from src.task_management.domain.value_objects.task_status import TaskStatus


class TaskStatusPolicy:
    """Encapsulates lifecycle rules for Task status transitions."""

    @staticmethod
    def assert_can_start_progress(current: TaskStatus) -> None:
        if current is not TaskStatus.TODO:
            raise TaskTransitionError(
                f"Only TODO tasks can start progress (current={current.value!r})"
            )

    @staticmethod
    def assert_has_assignee(assignee_is_set: bool) -> None:
        if not assignee_is_set:
            raise TaskDomainError("Cannot start a task without an assignee")

    @staticmethod
    def assert_can_complete(current: TaskStatus) -> None:
        if current is not TaskStatus.IN_PROGRESS:
            raise TaskTransitionError(
                f"Only IN_PROGRESS tasks can be completed (current={current.value!r})"
            )

    @staticmethod
    def assert_can_return_to_todo(current: TaskStatus) -> None:
        if current is not TaskStatus.IN_PROGRESS:
            raise TaskTransitionError(
                f"Only IN_PROGRESS tasks can return to TODO (current={current.value!r})"
            )

    @staticmethod
    def assert_can_reopen(current: TaskStatus) -> None:
        if current is not TaskStatus.DONE:
            raise TaskTransitionError(
                f"Only DONE tasks can be reopened (current={current.value!r})"
            )

    @staticmethod
    def assert_can_change_assignee(current: TaskStatus) -> None:
        if current is not TaskStatus.TODO:
            raise TaskDomainError("Assignee can only be changed while the task is TODO")

    @staticmethod
    def assert_can_change_details(current: TaskStatus) -> None:
        if current is TaskStatus.DONE:
            raise TaskDomainError("Cannot change details of a completed task; reopen it first")

    @staticmethod
    def assert_can_delete(current: TaskStatus) -> None:
        if current is not TaskStatus.TODO:
            raise TaskDomainError("Only TODO tasks can be deleted")
