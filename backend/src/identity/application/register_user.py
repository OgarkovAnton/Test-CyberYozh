from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from src.shared_kernel.domain.errors import DomainError

User = get_user_model()


class EmailAlreadyExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Email is already registered", code="EmailAlreadyExists")


class WeakPasswordError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="WeakPassword")


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""


@dataclass(frozen=True, slots=True)
class RegisteredUser:
    id: str
    email: str


class RegisterUserUseCase:
    def execute(self, command: RegisterUserCommand) -> RegisteredUser:
        try:
            validate_password(command.password)
        except ValidationError as exc:
            raise WeakPasswordError(" ".join(exc.messages)) from exc
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=command.email.strip().lower(),
                    password=command.password,
                    first_name=command.first_name.strip(),
                    last_name=command.last_name.strip(),
                )
        except IntegrityError as exc:
            raise EmailAlreadyExistsError() from exc
        return RegisteredUser(id=str(user.id), email=user.email)
