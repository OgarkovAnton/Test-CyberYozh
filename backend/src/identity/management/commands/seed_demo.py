from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId
from src.task_management.application.commands import (
    AddCommentCommand,
    AddCommentUseCase,
    AssignTaskCommand,
    AssignTaskUseCase,
    CreateTaskCommand,
    CreateTaskUseCase,
)
from src.task_management.infrastructure.persistence.models import TaskModel

User = get_user_model()
DEMO_TITLE = "Prepare architecture review"


class Command(BaseCommand):
    help = "Seed demo users and a sample task"

    def handle(self, *args, **options):
        admin = User.objects.filter(email="admin@example.com").first()
        if admin is None:
            admin = User.objects.create_user(
                email="admin@example.com",
                password="password123",
                first_name="Admin",
                is_staff=True,
            )

        bob = User.objects.filter(email="bob@example.com").first()
        if bob is None:
            bob = User.objects.create_user(
                email="bob@example.com",
                password="password123",
                first_name="Bob",
            )

        if TaskModel.objects.filter(creator=admin, title=DEMO_TITLE).exists():
            self.stdout.write(self.style.SUCCESS("Demo data already present"))
            return

        actor = ActorContext.of(UserId(admin.id))
        task = CreateTaskUseCase().execute(
            CreateTaskCommand(
                title=DEMO_TITLE,
                description="Review Task aggregate and outbox flow",
                actor=actor,
            )
        )
        AssignTaskUseCase().execute(
            AssignTaskCommand(
                task_id=task.id,
                assignee_id=str(bob.id),
                actor=actor,
            )
        )
        AddCommentUseCase().execute(
            AddCommentCommand(
                task_id=task.id,
                body="Let's keep domain rules in the aggregate.",
                actor=actor,
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data ready: admin@example.com (admin) / bob@example.com (password: password123)"
            )
        )
