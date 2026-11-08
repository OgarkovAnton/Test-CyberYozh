from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.shared_kernel.domain.errors import InvariantViolationError
from src.shared_kernel.domain.identifiers import UserId


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Who is performing an action and when (application → domain boundary)."""

    user_id: UserId
    occurred_at: datetime
    correlation_id: str | None = None
    is_staff: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.user_id, UserId):
            raise InvariantViolationError("ActorContext.user_id must be a UserId")
        if self.occurred_at.tzinfo is None:
            raise InvariantViolationError("ActorContext.occurred_at must be timezone-aware")

    @classmethod
    def of(
        cls,
        user_id: UserId,
        *,
        correlation_id: str | None = None,
        is_staff: bool = False,
    ) -> ActorContext:
        return cls(
            user_id=user_id,
            occurred_at=datetime.now(UTC),
            correlation_id=correlation_id,
            is_staff=is_staff,
        )
