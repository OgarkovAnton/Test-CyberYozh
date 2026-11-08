from __future__ import annotations

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from src.identity.application.register_user import RegisterUserCommand, RegisterUserUseCase
from src.identity.presentation.serializers import (
    RegisterSerializer,
    UserListSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=["Auth"],
        summary="Регистрация",
        description="Пароль проходит Django-валидаторы. is_staff не выставляется.",
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registered = RegisterUserUseCase().execute(
            RegisterUserCommand(**serializer.validated_data)
        )
        user = User.objects.get(id=registered.id)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema_view(get=extend_schema(tags=["Users"], summary="Текущий пользователь"))
class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


@extend_schema_view(
    get=extend_schema(
        tags=["Users"],
        summary="Активные пользователи",
        description="Список для назначения. Неактивные пользователи скрыты.",
    )
)
class UserListView(generics.ListAPIView):
    serializer_class = UserListSerializer
    queryset = User.objects.filter(is_active=True).order_by("email")
    pagination_class = None


@extend_schema_view(
    post=extend_schema(tags=["Auth"], summary="Получить access и refresh JWT")
)
class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


@extend_schema_view(post=extend_schema(tags=["Auth"], summary="Обновить access JWT"))
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
