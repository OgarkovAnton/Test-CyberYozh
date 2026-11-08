"""Shared kernel — cross-cutting domain primitives and ports."""

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.errors import DomainError, InvariantViolationError
from src.shared_kernel.domain.events import DomainEvent
from src.shared_kernel.domain.identifiers import UserId
from src.shared_kernel.domain.ports import OutboxPort, UnitOfWorkPort

__all__ = [
    "ActorContext",
    "DomainError",
    "DomainEvent",
    "InvariantViolationError",
    "OutboxPort",
    "UnitOfWorkPort",
    "UserId",
]
