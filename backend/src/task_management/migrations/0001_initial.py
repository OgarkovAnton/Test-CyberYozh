import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskModel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(db_index=True, max_length=32)),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assignee",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "creator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "tm_task",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="CommentModel",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="task_comments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="task_management.taskmodel",
                    ),
                ),
            ],
            options={
                "db_table": "tm_comment",
                "ordering": ("created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="taskmodel",
            index=models.Index(fields=["status"], name="tm_task_status_6d3d0b_idx"),
        ),
        migrations.AddIndex(
            model_name="taskmodel",
            index=models.Index(fields=["assignee", "status"], name="tm_task_assigne_0a5f0b_idx"),
        ),
        migrations.AddIndex(
            model_name="taskmodel",
            index=models.Index(fields=["creator", "status"], name="tm_task_creator_8f2a1c_idx"),
        ),
        migrations.AddIndex(
            model_name="commentmodel",
            index=models.Index(fields=["task", "created_at"], name="tm_comment_task_id_4e9b2a_idx"),
        ),
    ]
