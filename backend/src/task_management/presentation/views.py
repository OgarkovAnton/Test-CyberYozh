from __future__ import annotations

from dataclasses import asdict

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from src.task_management.application.commands import (
    AddCommentCommand,
    AddCommentUseCase,
    AssignTaskCommand,
    AssignTaskUseCase,
    CompleteTaskUseCase,
    CreateTaskCommand,
    CreateTaskUseCase,
    DeleteTaskUseCase,
    EditCommentCommand,
    EditCommentUseCase,
    RemoveCommentCommand,
    RemoveCommentUseCase,
    ReopenTaskUseCase,
    ReturnTaskToTodoUseCase,
    StartProgressUseCase,
    TaskIdCommand,
    UpdateTaskCommand,
    UpdateTaskUseCase,
)
from src.task_management.application.dto import task_to_dto
from src.task_management.application.queries import (
    GetTaskQuery,
    GetTaskQueryService,
    ListTasksQuery,
    ListTasksQueryService,
)
from src.task_management.infrastructure.persistence.mappers import task_to_domain
from src.task_management.presentation.actor import actor_from_request
from src.task_management.presentation.serializers import (
    ApiErrorSerializer,
    AssignSerializer,
    CommentWriteSerializer,
    TaskListItemSerializer,
    TaskSerializer,
    TaskUpdateSerializer,
    TaskWriteSerializer,
)


class TaskListPagination(PageNumberPagination):
    page_size = 20


_ERROR = {400: ApiErrorSerializer, 403: ApiErrorSerializer, 409: ApiErrorSerializer}
_LIST_PARAMS = [
    OpenApiParameter("page", int, description="Номер страницы, по 20 задач."),
    OpenApiParameter(
        "status",
        str,
        enum=["todo", "in_progress", "done"],
        description="Неизвестное значение даёт 400.",
    ),
    OpenApiParameter("assignee", str, description="UUID исполнителя."),
    OpenApiParameter("creator", str, description="UUID создателя."),
    OpenApiParameter("search", str, description="Поиск по заголовку."),
]


def _task_response(dto, *, http_status=status.HTTP_200_OK):
    return Response(TaskSerializer(asdict(dto)).data, status=http_status)


class TaskListCreateView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Список задач",
        description="Общая доска: любой вошедший пользователь видит все задачи. Комментариев в списке нет.",
        parameters=_LIST_PARAMS,
        responses={200: TaskListItemSerializer(many=True), 400: ApiErrorSerializer},
    )
    def get(self, request):
        queryset = ListTasksQueryService().queryset(
            ListTasksQuery(
                actor=actor_from_request(request),
                status=request.query_params.get("status"),
                assignee_id=request.query_params.get("assignee"),
                creator_id=request.query_params.get("creator"),
                search=request.query_params.get("search"),
            )
        )
        paginator = TaskListPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        payload = [
            asdict(task_to_dto(task_to_domain(row, comments=[]))) for row in page
        ]
        return paginator.get_paginated_response(
            TaskListItemSerializer(payload, many=True).data
        )

    @extend_schema(
        tags=["Tasks"],
        summary="Создать задачу",
        description="Исполнитель необязателен. Неизвестный или неактивный assignee_id даёт 400.",
        request=TaskWriteSerializer,
        responses={201: TaskSerializer, 400: ApiErrorSerializer},
    )
    def post(self, request):
        serializer = TaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dto = CreateTaskUseCase().execute(
            CreateTaskCommand(
                title=data["title"],
                description=data.get("description", ""),
                assignee_id=str(data["assignee_id"]) if data.get("assignee_id") else None,
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto, http_status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Карточка задачи",
        responses={200: TaskSerializer, 404: ApiErrorSerializer},
    )
    def get(self, request, task_id):
        dto = GetTaskQueryService().execute(
            GetTaskQuery(task_id=str(task_id), actor=actor_from_request(request))
        )
        return _task_response(dto)

    @extend_schema(
        tags=["Tasks"],
        summary="Изменить заголовок и описание",
        description=(
            "Нужна version из последнего чтения. Если задачу уже изменили, ответ 409. "
            "Поле assignee_id здесь запрещено: назначение делается через POST /assign/."
        ),
        request=TaskUpdateSerializer,
        responses={200: TaskSerializer, **_ERROR},
    )
    def put(self, request, task_id):
        if "assignee_id" in request.data:
            return Response(
                {
                    "detail": "Assignee is changed with POST /assign/.",
                    "code": "AssigneeChangeNotAllowed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dto = UpdateTaskUseCase().execute(
            UpdateTaskCommand(
                task_id=str(task_id),
                title=data["title"],
                description=data.get("description", ""),
                version=data["version"],
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto)

    @extend_schema(
        tags=["Tasks"],
        summary="Удалить задачу",
        description="Только создатель или PM, и только из статуса todo.",
        responses={204: None, 400: ApiErrorSerializer, 403: ApiErrorSerializer},
    )
    def delete(self, request, task_id):
        DeleteTaskUseCase().execute(
            TaskIdCommand(task_id=str(task_id), actor=actor_from_request(request))
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskAssignView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Назначить или снять исполнителя",
        description="Только в статусе todo. assignee_id: null снимает исполнителя. В in_progress и done поле заморожено.",
        request=AssignSerializer,
        responses={200: TaskSerializer, **_ERROR},
    )
    def post(self, request, task_id):
        serializer = AssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_assignee = serializer.validated_data["assignee_id"]
        dto = AssignTaskUseCase().execute(
            AssignTaskCommand(
                task_id=str(task_id),
                assignee_id=str(raw_assignee) if raw_assignee else None,
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto)


class TaskStartView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Начать работу",
        description="Только из todo и только если исполнитель уже назначен. Иначе 400.",
        responses={200: TaskSerializer, **_ERROR},
    )
    def post(self, request, task_id):
        dto = StartProgressUseCase().execute(
            TaskIdCommand(task_id=str(task_id), actor=actor_from_request(request))
        )
        return _task_response(dto)


class TaskReturnView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Вернуть в очередь",
        description="in_progress → todo. Исполнитель сохраняется, completed_at не ставится.",
        responses={200: TaskSerializer, **_ERROR},
    )
    def post(self, request, task_id):
        dto = ReturnTaskToTodoUseCase().execute(
            TaskIdCommand(task_id=str(task_id), actor=actor_from_request(request))
        )
        return _task_response(dto)


class TaskCompleteView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Завершить задачу",
        description="Только из in_progress. Прямой переход из todo запрещён.",
        responses={200: TaskSerializer, **_ERROR},
    )
    def post(self, request, task_id):
        dto = CompleteTaskUseCase().execute(
            TaskIdCommand(task_id=str(task_id), actor=actor_from_request(request))
        )
        return _task_response(dto)


class TaskReopenView(APIView):
    @extend_schema(
        tags=["Tasks"],
        summary="Переоткрыть задачу",
        description="done → todo. Исполнитель сохраняется.",
        responses={200: TaskSerializer, **_ERROR},
    )
    def post(self, request, task_id):
        dto = ReopenTaskUseCase().execute(
            TaskIdCommand(task_id=str(task_id), actor=actor_from_request(request))
        )
        return _task_response(dto)


class TaskCommentsView(APIView):
    @extend_schema(
        tags=["Comments"],
        summary="Добавить комментарий",
        description="Любой вошедший пользователь, в любом статусе, включая done.",
        request=CommentWriteSerializer,
        responses={201: TaskSerializer, 400: ApiErrorSerializer},
    )
    def post(self, request, task_id):
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dto = AddCommentUseCase().execute(
            AddCommentCommand(
                task_id=str(task_id),
                body=serializer.validated_data["body"],
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto, http_status=status.HTTP_201_CREATED)


class CommentDetailView(APIView):
    @extend_schema(
        tags=["Comments"],
        summary="Изменить свой комментарий",
        request=CommentWriteSerializer,
        responses={200: TaskSerializer, 403: ApiErrorSerializer, 404: ApiErrorSerializer},
    )
    def put(self, request, task_id, comment_id):
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dto = EditCommentUseCase().execute(
            EditCommentCommand(
                task_id=str(task_id),
                comment_id=str(comment_id),
                body=serializer.validated_data["body"],
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto)

    @extend_schema(
        tags=["Comments"],
        summary="Удалить свой комментарий",
        responses={200: TaskSerializer, 403: ApiErrorSerializer, 404: ApiErrorSerializer},
    )
    def delete(self, request, task_id, comment_id):
        dto = RemoveCommentUseCase().execute(
            RemoveCommentCommand(
                task_id=str(task_id),
                comment_id=str(comment_id),
                actor=actor_from_request(request),
            )
        )
        return _task_response(dto)
