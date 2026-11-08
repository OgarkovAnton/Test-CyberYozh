from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from src.shared_kernel.domain.errors import DomainError, InvariantViolationError
from src.task_management.domain.errors import (
    CommentNotFoundError,
    CommentPermissionError,
    TaskConflictError,
    TaskNotFoundError,
    TaskPermissionError,
    TaskTransitionError,
)


_STATUS_MAP: dict[type[Exception], int] = {
    TaskNotFoundError: status.HTTP_404_NOT_FOUND,
    CommentNotFoundError: status.HTTP_404_NOT_FOUND,
    TaskPermissionError: status.HTTP_403_FORBIDDEN,
    CommentPermissionError: status.HTTP_403_FORBIDDEN,
    TaskTransitionError: status.HTTP_409_CONFLICT,
    TaskConflictError: status.HTTP_409_CONFLICT,
    InvariantViolationError: status.HTTP_400_BAD_REQUEST,
}


def domain_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, DomainError):
        http_status = status.HTTP_400_BAD_REQUEST
        for error_type, mapped in _STATUS_MAP.items():
            if isinstance(exc, error_type):
                http_status = mapped
                break
        return Response(
            {"detail": exc.message, "code": exc.code},
            status=http_status,
        )
    return None
