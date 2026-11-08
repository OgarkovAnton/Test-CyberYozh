from __future__ import annotations

from django.urls import path

from src.identity.presentation.views import (
    LoginView,
    MeView,
    RefreshView,
    RegisterView,
    UserListView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/token/", LoginView.as_view(), name="auth-token"),
    path("auth/token/refresh/", RefreshView.as_view(), name="auth-token-refresh"),
    path("users/me/", MeView.as_view(), name="users-me"),
    path("users/", UserListView.as_view(), name="users-list"),
]
