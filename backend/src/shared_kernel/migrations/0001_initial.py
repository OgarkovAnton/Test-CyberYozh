import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OutboxMessage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("event_id", models.UUIDField(unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=128)),
                ("aggregate_type", models.CharField(blank=True, default="", max_length=64)),
                ("aggregate_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("processed_at", models.DateTimeField(blank=True, db_index=True, null=True)),
            ],
            options={
                "db_table": "shared_outbox_message",
                "ordering": ("created_at",),
            },
        ),
    ]
