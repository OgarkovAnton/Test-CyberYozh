from __future__ import annotations

from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.entities.comment import Comment
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.comment_id import CommentId
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_status import TaskStatus
from src.task_management.domain.value_objects.task_title import TaskTitle
from src.task_management.infrastructure.persistence.models import CommentModel, TaskModel


def comment_to_domain(row: CommentModel) -> Comment:
    comment = Comment(
        id=CommentId(row.id),
        author_id=UserId(row.author_id),
        body=CommentBody(row.body),
        created_at=row.created_at,
    )
    comment.updated_at = row.updated_at
    return comment


def task_to_domain(row: TaskModel, comments: list[CommentModel] | None = None) -> Task:
    comment_rows = comments if comments is not None else list(row.comments.all())
    return Task.rehydrate(
        id=TaskId(row.id),
        title=TaskTitle(row.title),
        description=row.description,
        creator_id=UserId(row.creator_id),
        status=TaskStatus(row.status),
        assignee_id=UserId(row.assignee_id) if row.assignee_id else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
        comments=[comment_to_domain(c) for c in comment_rows],
        version=row.version,
    )


def apply_task_to_model(task: Task, row: TaskModel) -> None:
    row.title = task.title.value
    row.description = task.description
    row.status = task.status.value
    row.creator_id = task.creator_id.value
    row.assignee_id = task.assignee_id.value if task.assignee_id else None
    row.created_at = task.created_at
    row.updated_at = task.updated_at
    row.completed_at = task.completed_at
    row.version = task.version
