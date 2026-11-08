from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from src.notifications.infrastructure.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "event_type", "payload", "created_at", "read_at")
        read_only_fields = fields


@extend_schema_view(
    get=extend_schema(
        tags=["Notifications"],
        summary="Мои уведомления",
        description="Полный список без пагинации. Источник правды для ящика; SSE только будит клиент.",
    )
)
class MyNotificationsView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    pagination_class = None

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class MarkNotificationReadView(APIView):
    @extend_schema(
        tags=["Notifications"],
        summary="Отметить уведомление прочитанным",
        description="Чужое или несуществующее уведомление даёт 404.",
        request=None,
        responses={200: NotificationSerializer, 404: None},
    )
    def post(self, request, notification_id):
        try:
            note = Notification.objects.get(id=notification_id, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if note.read_at is None:
            note.read_at = timezone.now()
            note.save(update_fields=["read_at"])
        return Response(NotificationSerializer(note).data)
