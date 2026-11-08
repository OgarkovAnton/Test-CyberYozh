from __future__ import annotations

import uuid

from django.db import models


class OutboxMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(unique=True)
    event_type = models.CharField(max_length=128, db_index=True)
    aggregate_type = models.CharField(max_length=64, blank=True, default="")
    aggregate_id = models.UUIDField(null=True, blank=True, db_index=True)
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    dead_lettered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "shared_outbox_message"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.event_type}:{self.event_id}"
