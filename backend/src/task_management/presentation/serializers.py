from __future__ import annotations

from rest_framework import serializers


class CommentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    author_id = serializers.UUIDField(read_only=True)
    body = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=4000
    )
    status = serializers.CharField(read_only=True)
    creator_id = serializers.UUIDField(read_only=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    version = serializers.IntegerField(
        read_only=True,
        help_text="Текущая версия агрегата. Её нужно вернуть в PUT.",
    )
    comments = CommentSerializer(many=True, read_only=True)


class TaskListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=4000
    )
    status = serializers.CharField(read_only=True)
    creator_id = serializers.UUIDField(read_only=True)
    assignee_id = serializers.UUIDField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True, allow_null=True)
    version = serializers.IntegerField(read_only=True)


class TaskWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=4000
    )
    assignee_id = serializers.UUIDField(required=False, allow_null=True)


class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=4000
    )
    version = serializers.IntegerField(
        min_value=1,
        help_text="Версия, полученная в последнем GET. Чужое сохранение даёт 409.",
    )


class ApiErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()


class AssignSerializer(serializers.Serializer):
    assignee_id = serializers.UUIDField(allow_null=True)


class CommentWriteSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=4000)
