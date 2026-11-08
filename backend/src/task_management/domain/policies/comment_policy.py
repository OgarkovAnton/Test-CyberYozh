from __future__ import annotations

from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.entities.comment import Comment
from src.task_management.domain.errors import CommentPermissionError


class CommentPolicy:
    """Rules for mutating comments inside a Task aggregate."""

    @staticmethod
    def assert_can_edit(comment: Comment, actor_id: UserId) -> None:
        if not comment.is_authored_by(actor_id):
            raise CommentPermissionError("Only the comment author can edit it")

    @staticmethod
    def assert_can_remove(comment: Comment, actor_id: UserId) -> None:
        if not comment.is_authored_by(actor_id):
            raise CommentPermissionError("Only the comment author can remove it")
