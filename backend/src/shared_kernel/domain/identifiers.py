from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.shared_kernel.domain.errors import InvariantViolationError


@dataclass(frozen=True, slots=True)
class UserId:
    """Strongly typed identity for a user across bounded contexts."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvariantViolationError("UserId must wrap a UUID instance")

    @classmethod
    def generate(cls) -> UserId:
        return cls(uuid4())

    @classmethod
    def from_str(cls, raw: str) -> UserId:
        try:
            return cls(UUID(raw))
        except (TypeError, ValueError) as exc:
            raise InvariantViolationError(f"Invalid UserId: {raw!r}") from exc

    def __str__(self) -> str:
        return str(self.value)
