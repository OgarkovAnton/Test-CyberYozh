from __future__ import annotations

from django.urls import path

from src.task_management.presentation.views import (
    CommentDetailView,
    TaskAssignView,
    TaskCommentsView,
    TaskCompleteView,
    TaskDetailView,
    TaskListCreateView,
    TaskReopenView,
    TaskReturnView,
    TaskStartView,
)

urlpatterns = [
    path("tasks/", TaskListCreateView.as_view(), name="task-list-create"),
    path("tasks/<uuid:task_id>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<uuid:task_id>/assign/", TaskAssignView.as_view(), name="task-assign"),
    path("tasks/<uuid:task_id>/start/", TaskStartView.as_view(), name="task-start"),
    path("tasks/<uuid:task_id>/return/", TaskReturnView.as_view(), name="task-return"),
    path("tasks/<uuid:task_id>/complete/", TaskCompleteView.as_view(), name="task-complete"),
    path("tasks/<uuid:task_id>/reopen/", TaskReopenView.as_view(), name="task-reopen"),
    path(
        "tasks/<uuid:task_id>/comments/",
        TaskCommentsView.as_view(),
        name="task-comments",
    ),
    path(
        "tasks/<uuid:task_id>/comments/<uuid:comment_id>/",
        CommentDetailView.as_view(),
        name="comment-detail",
    ),
]
