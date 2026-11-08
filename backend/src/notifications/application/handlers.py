from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.contrib.auth import get_user_model

from src.notifications.application.publish import publish_notification
from src.notifications.infrastructure.models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


def handle_domain_event(payload: dict[str, Any]) -> None:
    event_type = payload.get("event_type")
    event_id = payload.get("event_id")
    if not event_type or not event_id:
        return

    if event_type == "TaskAssigned":
        _on_task_assigned(payload)
    elif event_type == "CommentAdded":
        _on_comment_added(payload)
    else:
        logger.debug("Ignoring event type %s", event_type)


def _notify(payload: dict[str, Any], recipient_id: str, event_type: str) -> None:
    if not User.objects.filter(id=recipient_id, is_active=True).exists():
        return
    note, created = Notification.objects.get_or_create(
        event_id=UUID(str(payload["event_id"])),
        recipient_id=recipient_id,
        defaults={
            "event_type": event_type,
            "payload": payload,
        },
    )
    if created:
        publish_notification(
            recipient_id,
            {
                "id": str(note.id),
                "event_type": note.event_type,
                "created_at": note.created_at.isoformat(),
            },
        )


def _on_task_assigned(payload: dict[str, Any]) -> None:
    actor_id = str(payload["actor_id"]) if payload.get("actor_id") else None
    assignee_id = payload.get("assignee_id")
    previous_id = payload.get("previous_assignee_id")

    if assignee_id and str(assignee_id) != actor_id:
        _notify(payload, str(assignee_id), "TaskAssigned")
        logger.info("Notification created for TaskAssigned → %s", assignee_id)

    cleared_ids = {actor_id}
    if assignee_id:
        cleared_ids.add(str(assignee_id))
    if previous_id and str(previous_id) not in cleared_ids:
        _notify(payload, str(previous_id), "AssigneeCleared")
        logger.info("Notification created for AssigneeCleared → %s", previous_id)


def _on_comment_added(payload: dict[str, Any]) -> None:
    author_id = str(payload["author_id"]) if payload.get("author_id") else None
    recipients: set[str] = set()
    if payload.get("creator_id"):
        recipients.add(str(payload["creator_id"]))
    if payload.get("assignee_id"):
        recipients.add(str(payload["assignee_id"]))
    if author_id:
        recipients.discard(author_id)

    for recipient_id in recipients:
        _notify(payload, recipient_id, "CommentAdded")
    logger.info(
        "Notifications created for CommentAdded on task %s",
        payload.get("aggregate_id"),
    )
