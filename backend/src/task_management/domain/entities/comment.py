from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.comment_id import CommentId


@dataclass(slots=True)
class Comment:
    """Comment entity owned by the Task aggregate root."""

    id: CommentId
    author_id: UserId
    body: CommentBody
    created_at: datetime
    updated_at: datetime = field(init=False)

    def __post_init__(self) -> None:
        self.updated_at = self.created_at

    def edit(self, body: CommentBody, *, edited_at: datetime | None = None) -> None:
        self.body = body
        self.updated_at = edited_at or datetime.now(UTC)

    def is_authored_by(self, user_id: UserId) -> bool:
        return self.author_id == user_id
