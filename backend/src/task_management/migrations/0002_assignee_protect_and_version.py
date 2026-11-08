import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("task_management", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskmodel",
            name="version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="taskmodel",
            name="status",
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name="taskmodel",
            name="assignee",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assigned_tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
