from __future__ import annotations

from django.urls import path

from src.notifications.presentation.stream import NotificationStreamView
from src.notifications.presentation.views import MarkNotificationReadView, MyNotificationsView

urlpatterns = [
    path("notifications/stream/", NotificationStreamView.as_view(), name="notifications-stream"),
    path("notifications/me/", MyNotificationsView.as_view(), name="notifications-me"),
    path(
        "notifications/<uuid:notification_id>/read/",
        MarkNotificationReadView.as_view(),
        name="notification-read",
    ),
]
