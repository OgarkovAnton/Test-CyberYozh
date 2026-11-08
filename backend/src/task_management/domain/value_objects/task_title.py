from __future__ import annotations

from dataclasses import dataclass

from src.shared_kernel.domain.errors import InvariantViolationError

_MIN_LENGTH = 1
_MAX_LENGTH = 200


@dataclass(frozen=True, slots=True)
class TaskTitle:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvariantViolationError("TaskTitle must be a string")
        normalized = self.value.strip()
        if len(normalized) < _MIN_LENGTH:
            raise InvariantViolationError("TaskTitle must not be empty")
        if len(normalized) > _MAX_LENGTH:
            raise InvariantViolationError(
                f"TaskTitle must be at most {_MAX_LENGTH} characters"
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
