from __future__ import annotations

from datetime import UTC, datetime

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.aggregate import AggregateRoot
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.entities.comment import Comment
from src.shared_kernel.domain.errors import InvariantViolationError
from src.task_management.domain.errors import CommentNotFoundError
from src.task_management.domain.events.task_events import (
    CommentAdded,
    CommentEdited,
    CommentRemoved,
    TaskAssigned,
    TaskCompleted,
    TaskCreated,
    TaskDetailsChanged,
    TaskProgressStarted,
    TaskReopened,
    TaskReturnedToTodo,
)
from src.task_management.domain.policies.access_policy import TaskAccessPolicy
from src.task_management.domain.policies.comment_policy import CommentPolicy
from src.task_management.domain.policies.task_status_policy import TaskStatusPolicy
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.comment_id import CommentId
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_status import TaskStatus
from src.task_management.domain.value_objects.task_title import TaskTitle

_MAX_DESCRIPTION_LENGTH = 4000


def _normalize_description(value: str) -> str:
    if not isinstance(value, str):
        raise InvariantViolationError("Description must be a string")
    normalized = value.strip()
    if len(normalized) > _MAX_DESCRIPTION_LENGTH:
        raise InvariantViolationError(
            f"Description must be at most {_MAX_DESCRIPTION_LENGTH} characters"
        )
    return normalized


class Task(AggregateRoot):
    """Task aggregate root — consistency boundary for task + comments."""

    def __init__(
        self,
        *,
        id: TaskId,
        title: TaskTitle,
        description: str,
        creator_id: UserId,
        status: TaskStatus,
        assignee_id: UserId | None,
        created_at: datetime,
        updated_at: datetime,
        completed_at: datetime | None,
        comments: list[Comment] | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self._id = id
        self._title = title
        self._description = description
        self._creator_id = creator_id
        self._status = status
        self._assignee_id = assignee_id
        self._created_at = created_at
        self._updated_at = updated_at
        self._completed_at = completed_at
        self._version = version
        self._loaded_version = version
        self._comments: dict[CommentId, Comment] = {
            comment.id: comment for comment in (comments or [])
        }

    @classmethod
    def create(
        cls,
        *,
        title: TaskTitle,
        description: str,
        creator: ActorContext,
        assignee_id: UserId | None = None,
        task_id: TaskId | None = None,
    ) -> Task:
        now = creator.occurred_at
        task = cls(
            id=task_id or TaskId.generate(),
            title=title,
            description=_normalize_description(description),
            creator_id=creator.user_id,
            status=TaskStatus.TODO,
            assignee_id=assignee_id,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        task._record(
            TaskCreated(
                aggregate_id=task.id.value,
                aggregate_type="Task",
                actor_id=creator.user_id.value,
                title=task.title.value,
                description=task.description,
                creator_id=task.creator_id.value,
                assignee_id=task.assignee_id.value if task.assignee_id else None,
            )
        )
        if assignee_id is not None:
            task._record(
                TaskAssigned(
                    aggregate_id=task.id.value,
                    aggregate_type="Task",
                    actor_id=creator.user_id.value,
                    assignee_id=assignee_id.value,
                    previous_assignee_id=None,
                )
            )
        return task

    # --- properties (read-only surface) ---

    @property
    def id(self) -> TaskId:
        return self._id

    @property
    def title(self) -> TaskTitle:
        return self._title

    @property
    def description(self) -> str:
        return self._description

    @property
    def creator_id(self) -> UserId:
        return self._creator_id

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def assignee_id(self) -> UserId | None:
        return self._assignee_id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def comments(self) -> tuple[Comment, ...]:
        return tuple(sorted(self._comments.values(), key=lambda c: c.created_at))

    @property
    def version(self) -> int:
        return self._version

    @property
    def loaded_version(self) -> int:
        return self._loaded_version

    def get_comment(self, comment_id: CommentId) -> Comment:
        comment = self._comments.get(comment_id)
        if comment is None:
            raise CommentNotFoundError(f"Comment {comment_id} not found on task {self.id}")
        return comment

    # --- commands ---

    def change_details(
        self,
        *,
        title: TaskTitle,
        description: str,
        actor: ActorContext,
    ) -> None:
        TaskAccessPolicy.assert_can_edit(creator_id=self._creator_id, actor=actor)
        TaskStatusPolicy.assert_can_change_details(self._status)
        description = _normalize_description(description)
        if self._title == title and self._description == description:
            return
        self._title = title
        self._description = description
        self._touch(actor.occurred_at)
        self._record(
            TaskDetailsChanged(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                title=self._title.value,
                description=self._description,
            )
        )

    def assign(self, *, assignee_id: UserId | None, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_assign(creator_id=self._creator_id, actor=actor)
        TaskStatusPolicy.assert_can_change_assignee(self._status)
        previous = self._assignee_id
        if previous == assignee_id:
            return
        self._assignee_id = assignee_id
        self._touch(actor.occurred_at)
        self._record(
            TaskAssigned(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                assignee_id=assignee_id.value if assignee_id else None,
                previous_assignee_id=previous.value if previous else None,
            )
        )

    def start_progress(self, *, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_change_status(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )
        TaskStatusPolicy.assert_can_start_progress(self._status)
        TaskStatusPolicy.assert_has_assignee(self._assignee_id is not None)
        self._status = self._status.transition_to(TaskStatus.IN_PROGRESS)
        self._touch(actor.occurred_at)
        self._record(
            TaskProgressStarted(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                started_by=actor.user_id.value,
            )
        )

    def complete(self, *, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_change_status(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )
        TaskStatusPolicy.assert_can_complete(self._status)
        self._status = self._status.transition_to(TaskStatus.DONE)
        self._completed_at = actor.occurred_at
        self._touch(actor.occurred_at)
        self._record(
            TaskCompleted(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                completed_by=actor.user_id.value,
            )
        )

    def return_to_todo(self, *, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_change_status(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )
        TaskStatusPolicy.assert_can_return_to_todo(self._status)
        self._status = self._status.transition_to(TaskStatus.TODO)
        self._touch(actor.occurred_at)
        self._record(
            TaskReturnedToTodo(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                returned_by=actor.user_id.value,
            )
        )

    def reopen(self, *, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_change_status(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )
        TaskStatusPolicy.assert_can_reopen(self._status)
        self._status = self._status.transition_to(TaskStatus.TODO)
        self._completed_at = None
        self._touch(actor.occurred_at)
        self._record(
            TaskReopened(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                reopened_by=actor.user_id.value,
            )
        )

    def add_comment(
        self,
        *,
        body: CommentBody,
        actor: ActorContext,
        comment_id: CommentId | None = None,
    ) -> Comment:
        TaskAccessPolicy.assert_can_comment(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )
        comment = Comment(
            id=comment_id or CommentId.generate(),
            author_id=actor.user_id,
            body=body,
            created_at=actor.occurred_at,
        )
        self._comments[comment.id] = comment
        self._touch(actor.occurred_at)
        self._record(
            CommentAdded(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                comment_id=comment.id.value,
                author_id=actor.user_id.value,
                body=body.value,
                creator_id=self._creator_id.value,
                assignee_id=self._assignee_id.value if self._assignee_id else None,
            )
        )
        return comment

    def edit_comment(
        self,
        *,
        comment_id: CommentId,
        body: CommentBody,
        actor: ActorContext,
    ) -> Comment:
        comment = self.get_comment(comment_id)
        CommentPolicy.assert_can_edit(comment, actor.user_id)
        comment.edit(body, edited_at=actor.occurred_at)
        self._touch(actor.occurred_at)
        self._record(
            CommentEdited(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                comment_id=comment.id.value,
                editor_id=actor.user_id.value,
                body=body.value,
            )
        )
        return comment

    def remove_comment(self, *, comment_id: CommentId, actor: ActorContext) -> None:
        comment = self.get_comment(comment_id)
        CommentPolicy.assert_can_remove(comment, actor.user_id)
        del self._comments[comment_id]
        self._touch(actor.occurred_at)
        self._record(
            CommentRemoved(
                aggregate_id=self.id.value,
                aggregate_type="Task",
                actor_id=actor.user_id.value,
                comment_id=comment_id.value,
                removed_by=actor.user_id.value,
            )
        )

    def assert_visible_to(self, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_view(
            creator_id=self._creator_id,
            assignee_id=self._assignee_id,
            actor=actor,
        )

    def assert_deletable_by(self, actor: ActorContext) -> None:
        TaskAccessPolicy.assert_can_delete(creator_id=self._creator_id, actor=actor)
        TaskStatusPolicy.assert_can_delete(self._status)

    def _touch(self, when: datetime | None = None) -> None:
        self._updated_at = when or datetime.now(UTC)
        self._version += 1

    @classmethod
    def rehydrate(
        cls,
        *,
        id: TaskId,
        title: TaskTitle,
        description: str,
        creator_id: UserId,
        status: TaskStatus,
        assignee_id: UserId | None,
        created_at: datetime,
        updated_at: datetime,
        completed_at: datetime | None,
        comments: list[Comment] | None = None,
        version: int = 1,
    ) -> Task:
        """Rebuild aggregate from persistence without recording events."""
        return cls(
            id=id,
            title=title,
            description=description,
            creator_id=creator_id,
            status=status,
            assignee_id=assignee_id,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            comments=comments,
            version=version,
        )
