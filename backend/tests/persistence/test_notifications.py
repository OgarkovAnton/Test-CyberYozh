from __future__ import annotations

from uuid import uuid4

import pytest

from src.notifications.application.handlers import handle_domain_event
from src.notifications.application.publish import publish_notification
from src.notifications.infrastructure.models import Notification


def _event(event_type: str, **payload) -> dict:
    return {"event_type": event_type, "event_id": str(uuid4()), **payload}


@pytest.mark.django_db
def test_assignment_notifies_the_new_assignee_once(user, other_user, monkeypatch):
    published: list[str] = []
    monkeypatch.setattr(
        "src.notifications.application.handlers.publish_notification",
        lambda recipient_id, _message: published.append(recipient_id),
    )
    payload = _event(
        "TaskAssigned",
        actor_id=str(user.id),
        assignee_id=str(other_user.id),
        previous_assignee_id=None,
    )
    handle_domain_event(payload)
    handle_domain_event(payload)
    assert published == [str(other_user.id)]
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_clearing_assignee_notifies_the_previous_one(user, other_user, monkeypatch):
    published: list[tuple[str, str]] = []

    def capture(recipient_id, message):
        published.append((recipient_id, message["event_type"]))

    monkeypatch.setattr(
        "src.notifications.application.handlers.publish_notification",
        capture,
    )
    handle_domain_event(
        _event(
            "TaskAssigned",
            actor_id=str(user.id),
            assignee_id=None,
            previous_assignee_id=str(other_user.id),
        )
    )
    assert published == [(str(other_user.id), "AssigneeCleared")]


@pytest.mark.django_db
def test_comment_notifies_creator_and_assignee_except_the_author(user, other_user, monkeypatch):
    published: list[str] = []
    monkeypatch.setattr(
        "src.notifications.application.handlers.publish_notification",
        lambda recipient_id, _message: published.append(recipient_id),
    )
    stranger = user.__class__.objects.create_user(email="eve@example.com", password="password123")
    handle_domain_event(
        _event(
            "CommentAdded",
            author_id=str(stranger.id),
            creator_id=str(user.id),
            assignee_id=str(other_user.id),
        )
    )
    assert set(published) == {str(user.id), str(other_user.id)}

    published.clear()
    handle_domain_event(
        _event(
            "CommentAdded",
            author_id=str(user.id),
            creator_id=str(user.id),
            assignee_id=None,
        )
    )
    assert published == []


@pytest.mark.django_db
def test_handler_skips_inactive_recipients_and_unknown_events(user, monkeypatch):
    published: list[str] = []
    monkeypatch.setattr(
        "src.notifications.application.handlers.publish_notification",
        lambda recipient_id, _message: published.append(recipient_id),
    )
    user.is_active = False
    user.save(update_fields=["is_active"])
    handle_domain_event(
        _event(
            "TaskAssigned",
            actor_id=str(uuid4()),
            assignee_id=str(user.id),
        )
    )
    handle_domain_event(_event("TaskCreated", actor_id=str(user.id)))
    handle_domain_event({"event_type": "TaskAssigned"})
    assert published == []
    assert Notification.objects.count() == 0


def test_publish_notification_swallows_redis_errors(monkeypatch):
    def explode(_url):
        raise ConnectionError("redis down")

    monkeypatch.setattr("src.notifications.application.publish.Redis.from_url", explode)
    publish_notification(str(uuid4()), {"id": "1", "event_type": "TaskAssigned"})
