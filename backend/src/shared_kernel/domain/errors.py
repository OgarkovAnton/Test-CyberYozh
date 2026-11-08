from __future__ import annotations


class DomainError(Exception):
    """Base exception for all domain rule violations."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class InvariantViolationError(DomainError):
    """Raised when an aggregate/value-object invariant is broken."""
