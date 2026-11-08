from __future__ import annotations

from django.db.models import Prefetch

from src.shared_kernel.domain.identifiers import UserId
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.errors import TaskConflictError
from src.task_management.domain.repositories import TaskQueryRepository, TaskRepository
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_status import TaskStatus
from src.task_management.infrastructure.persistence.mappers import (
    apply_task_to_model,
    task_to_domain,
)
from src.task_management.infrastructure.persistence.models import CommentModel, TaskModel


class DjangoTaskRepository(TaskRepository):
    def get(self, task_id: TaskId) -> Task | None:
        try:
            row = TaskModel.objects.prefetch_related("comments").get(id=task_id.value)
        except TaskModel.DoesNotExist:
            return None
        return task_to_domain(row)

    def add(self, task: Task) -> None:
        row = TaskModel(id=task.id.value)
        apply_task_to_model(task, row)
        row.save()
        self._sync_comments(task)

    def save(self, task: Task) -> None:
        if task.version == task.loaded_version:
            return
        row = TaskModel.objects.filter(id=task.id.value, version=task.loaded_version).first()
        if row is None:
            raise TaskConflictError()
        apply_task_to_model(task, row)
        updated = TaskModel.objects.filter(id=task.id.value, version=task.loaded_version).update(
            title=row.title,
            description=row.description,
            status=row.status,
            creator_id=row.creator_id,
            assignee_id=row.assignee_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
            completed_at=row.completed_at,
            version=row.version,
        )
        if updated != 1:
            raise TaskConflictError()
        self._sync_comments(task)

    def remove(self, task: Task) -> None:
        deleted, _ = TaskModel.objects.filter(
            id=task.id.value,
            version=task.loaded_version,
        ).delete()
        if deleted == 0:
            raise TaskConflictError()

    def _sync_comments(self, task: Task) -> None:
        existing = {
            str(cid): cid
            for cid in CommentModel.objects.filter(task_id=task.id.value).values_list(
                "id", flat=True
            )
        }
        keep: set[str] = set()
        for comment in task.comments:
            keep.add(str(comment.id.value))
            CommentModel.objects.update_or_create(
                id=comment.id.value,
                defaults={
                    "task_id": task.id.value,
                    "author_id": comment.author_id.value,
                    "body": comment.body.value,
                    "created_at": comment.created_at,
                    "updated_at": comment.updated_at,
                },
            )
        stale = set(existing) - keep
        if stale:
            CommentModel.objects.filter(id__in=stale).delete()


class DjangoTaskQueryRepository(TaskQueryRepository):
    def _detail_qs(self):
        return TaskModel.objects.prefetch_related(
            Prefetch("comments", queryset=CommentModel.objects.order_by("created_at"))
        )

    def filtered_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        assignee_id: UserId | None = None,
        creator_id: UserId | None = None,
        search: str | None = None,
    ):
        qs = TaskModel.objects.all()
        if status is not None:
            qs = qs.filter(status=status.value)
        if assignee_id is not None:
            qs = qs.filter(assignee_id=assignee_id.value)
        if creator_id is not None:
            qs = qs.filter(creator_id=creator_id.value)
        if search:
            qs = qs.filter(title__icontains=search.strip())
        return qs

    def list_tasks(
        self,
        *,
        viewer_id: UserId,
        is_staff: bool = False,
        status: TaskStatus | None = None,
        assignee_id: UserId | None = None,
        creator_id: UserId | None = None,
        search: str | None = None,
    ) -> list[Task]:
        del viewer_id, is_staff
        rows = self.filtered_tasks(
            status=status,
            assignee_id=assignee_id,
            creator_id=creator_id,
            search=search,
        )
        return [task_to_domain(row, comments=[]) for row in rows]

    def get_for_viewer(
        self,
        task_id: TaskId,
        *,
        viewer_id: UserId,
        is_staff: bool = False,
    ) -> Task | None:
        del viewer_id, is_staff
        try:
            row = self._detail_qs().get(id=task_id.value)
        except TaskModel.DoesNotExist:
            return None
        return task_to_domain(row)
