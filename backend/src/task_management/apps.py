from django.apps import AppConfig


class TaskManagementConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.task_management"
    label = "task_management"
    verbose_name = "Task Management"
