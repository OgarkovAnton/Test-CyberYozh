from __future__ import annotations

from enum import Enum

from src.task_management.domain.errors import TaskTransitionError


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

    def can_transition_to(self, target: TaskStatus) -> bool:
        return target in _ALLOWED_TRANSITIONS.get(self, frozenset())

    def transition_to(self, target: TaskStatus) -> TaskStatus:
        if self is target:
            return self
        if not self.can_transition_to(target):
            raise TaskTransitionError(
                f"Cannot transition task status from {self.value!r} to {target.value!r}"
            )
        return target


_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.TODO: frozenset({TaskStatus.IN_PROGRESS}),
    TaskStatus.IN_PROGRESS: frozenset({TaskStatus.DONE, TaskStatus.TODO}),
    TaskStatus.DONE: frozenset({TaskStatus.TODO}),
}
