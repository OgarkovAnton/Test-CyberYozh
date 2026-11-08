from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="alice@example.com", password="password123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="bob@example.com", password="password123")
