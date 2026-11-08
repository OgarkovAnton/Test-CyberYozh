from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.application.dto import TaskDTO, task_to_dto
from src.task_management.domain.errors import (
    AssigneeNotFoundError,
    TaskConflictError,
    TaskNotFoundError,
)
from src.task_management.domain.aggregates.task import Task
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.comment_id import CommentId
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.domain.value_objects.task_title import TaskTitle
from src.task_management.infrastructure.persistence.uow import DjangoUnitOfWork


@dataclass(frozen=True, slots=True)
class CreateTaskCommand:
    title: str
    description: str
    actor: ActorContext
    assignee_id: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTaskCommand:
    task_id: str
    title: str
    description: str
    version: int
    actor: ActorContext


@dataclass(frozen=True, slots=True)
class TaskIdCommand:
    task_id: str
    actor: ActorContext


@dataclass(frozen=True, slots=True)
class AssignTaskCommand:
    task_id: str
    assignee_id: str | None
    actor: ActorContext


@dataclass(frozen=True, slots=True)
class AddCommentCommand:
    task_id: str
    body: str
    actor: ActorContext


@dataclass(frozen=True, slots=True)
class EditCommentCommand:
    task_id: str
    comment_id: str
    body: str
    actor: ActorContext


@dataclass(frozen=True, slots=True)
class RemoveCommentCommand:
    task_id: str
    comment_id: str
    actor: ActorContext


def _require_active_assignee(assignee_id: str | None) -> None:
    if assignee_id is None:
        return
    user_model = get_user_model()
    if not user_model.objects.filter(id=assignee_id, is_active=True).exists():
        raise AssigneeNotFoundError()


def _load(uow: DjangoUnitOfWork, task_id: str) -> Task:
    task = uow.tasks.get(TaskId.from_str(task_id))
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return task


class CreateTaskUseCase:
    def execute(self, command: CreateTaskCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            _require_active_assignee(command.assignee_id)
            task = Task.create(
                title=TaskTitle(command.title),
                description=command.description,
                creator=command.actor,
                assignee_id=UserId.from_str(command.assignee_id)
                if command.assignee_id
                else None,
            )
            uow.register_new(task)
            uow.commit()
            return task_to_dto(task)


class UpdateTaskUseCase:
    def execute(self, command: UpdateTaskCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            if task.loaded_version != command.version:
                raise TaskConflictError()
            task.change_details(
                title=TaskTitle(command.title),
                description=command.description,
                actor=command.actor,
            )
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class DeleteTaskUseCase:
    def execute(self, command: TaskIdCommand) -> None:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.assert_deletable_by(command.actor)
            uow.register_removed(task)
            uow.commit()


class AssignTaskUseCase:
    def execute(self, command: AssignTaskCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            _require_active_assignee(command.assignee_id)
            task = _load(uow, command.task_id)
            task.assign(
                assignee_id=UserId.from_str(command.assignee_id) if command.assignee_id else None,
                actor=command.actor,
            )
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class StartProgressUseCase:
    def execute(self, command: TaskIdCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.start_progress(actor=command.actor)
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class ReturnTaskToTodoUseCase:
    def execute(self, command: TaskIdCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.return_to_todo(actor=command.actor)
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class CompleteTaskUseCase:
    def execute(self, command: TaskIdCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.complete(actor=command.actor)
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class ReopenTaskUseCase:
    def execute(self, command: TaskIdCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.reopen(actor=command.actor)
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class AddCommentUseCase:
    def execute(self, command: AddCommentCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.add_comment(body=CommentBody(command.body), actor=command.actor)
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class EditCommentUseCase:
    def execute(self, command: EditCommentCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.edit_comment(
                comment_id=CommentId.from_str(command.comment_id),
                body=CommentBody(command.body),
                actor=command.actor,
            )
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)


class RemoveCommentUseCase:
    def execute(self, command: RemoveCommentCommand) -> TaskDTO:
        with DjangoUnitOfWork() as uow:
            task = _load(uow, command.task_id)
            task.remove_comment(
                comment_id=CommentId.from_str(command.comment_id),
                actor=command.actor,
            )
            uow.register_dirty(task)
            uow.commit()
            return task_to_dto(task)
