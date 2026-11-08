from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    event_id = models.UUIDField(db_index=True)
    event_type = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "recipient"],
                name="uniq_notification_event_recipient",
            )
        ]
