from __future__ import annotations

from uuid import UUID

import pytest

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId
from src.shared_kernel.infrastructure.models import OutboxMessage
from src.task_management.application.commands import (
    CreateTaskCommand,
    CreateTaskUseCase,
)
from src.task_management.domain.errors import TaskConflictError
from src.task_management.domain.value_objects.comment_body import CommentBody
from src.task_management.domain.value_objects.task_id import TaskId
from src.task_management.infrastructure.persistence.repositories import DjangoTaskRepository


@pytest.mark.django_db
def test_stale_save_does_not_drop_a_newer_comment(user):
    actor = ActorContext.of(UserId(user.id))
    created = CreateTaskUseCase().execute(
        CreateTaskCommand(title="Race", description="d", actor=actor)
    )
    repo = DjangoTaskRepository()
    task_id = TaskId.from_str(created.id)
    first = repo.get(task_id)
    second = repo.get(task_id)
    assert first is not None and second is not None

    first.add_comment(body=CommentBody("kept"), actor=actor)
    repo.save(first)

    second.add_comment(body=CommentBody("lost"), actor=actor)
    with pytest.raises(TaskConflictError):
        repo.save(second)

    stored = repo.get(task_id)
    assert stored is not None
    assert [comment.body.value for comment in stored.comments] == ["kept"]


@pytest.mark.django_db
def test_relay_dead_letters_poison_messages(monkeypatch):
    from src.notifications.tasks import MAX_ATTEMPTS, relay_outbox

    OutboxMessage.objects.create(
        event_id=UUID("11111111-1111-1111-1111-111111111111"),
        event_type="TaskCreated",
        payload={"event_type": "TaskCreated", "event_id": "11111111-1111-1111-1111-111111111111"},
    )

    def explode(_payload):
        raise RuntimeError("handler down")

    monkeypatch.setattr("src.notifications.tasks.handle_domain_event", explode)
    for _ in range(MAX_ATTEMPTS):
        relay_outbox()

    message = OutboxMessage.objects.get()
    assert message.dead_lettered_at is not None
    assert message.attempts == MAX_ATTEMPTS
    relay_outbox()
    message.refresh_from_db()
    assert message.attempts == MAX_ATTEMPTS


@pytest.mark.django_db
def test_create_survives_broker_outage(user, django_capture_on_commit_callbacks, monkeypatch):
    def explode(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr("src.notifications.tasks.relay_outbox.delay", explode)
    actor = ActorContext.of(UserId(user.id))
    with django_capture_on_commit_callbacks(execute=True):
        created = CreateTaskUseCase().execute(
            CreateTaskCommand(title="Saved", description="d", actor=actor)
        )
    assert created.title == "Saved"
