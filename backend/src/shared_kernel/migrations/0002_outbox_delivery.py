from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shared_kernel", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="outboxmessage",
            name="attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="outboxmessage",
            name="dead_lettered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
