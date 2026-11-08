from __future__ import annotations

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.errors import TaskPermissionError


class TaskAccessPolicy:
    """Authorization rules for Task aggregate operations.

    Any authenticated actor may view a task and add a comment.
    PM is `ActorContext.is_staff`.
    """

    @staticmethod
    def _is_creator_or_staff(creator_id: UserId, actor: ActorContext) -> bool:
        return actor.is_staff or actor.user_id == creator_id

    @staticmethod
    def _can_change_status(
        creator_id: UserId,
        assignee_id: UserId | None,
        actor: ActorContext,
    ) -> bool:
        if actor.is_staff or actor.user_id == creator_id:
            return True
        return assignee_id is not None and actor.user_id == assignee_id

    @classmethod
    def assert_can_view(
        cls,
        *,
        creator_id: UserId,
        assignee_id: UserId | None,
        actor: ActorContext,
    ) -> None:
        del creator_id, assignee_id, actor

    @classmethod
    def assert_can_edit(cls, *, creator_id: UserId, actor: ActorContext) -> None:
        if not cls._is_creator_or_staff(creator_id, actor):
            raise TaskPermissionError("Only the creator or a PM can edit this task")

    @classmethod
    def assert_can_assign(cls, *, creator_id: UserId, actor: ActorContext) -> None:
        if not cls._is_creator_or_staff(creator_id, actor):
            raise TaskPermissionError("Only the creator or a PM can assign this task")

    @classmethod
    def assert_can_change_status(
        cls,
        *,
        creator_id: UserId,
        assignee_id: UserId | None,
        actor: ActorContext,
    ) -> None:
        if not cls._can_change_status(creator_id, assignee_id, actor):
            raise TaskPermissionError("Not allowed to change status of this task")

    @classmethod
    def assert_can_comment(
        cls,
        *,
        creator_id: UserId,
        assignee_id: UserId | None,
        actor: ActorContext,
    ) -> None:
        del creator_id, assignee_id, actor

    @classmethod
    def assert_can_delete(cls, *, creator_id: UserId, actor: ActorContext) -> None:
        if not cls._is_creator_or_staff(creator_id, actor):
            raise TaskPermissionError("Only the creator or a PM can delete this task")
