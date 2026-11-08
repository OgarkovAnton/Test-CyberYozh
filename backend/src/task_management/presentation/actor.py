from __future__ import annotations

from src.shared_kernel.domain.actor import ActorContext
from src.shared_kernel.domain.identifiers import UserId


def actor_from_request(request) -> ActorContext:
    return ActorContext.of(
        UserId(request.user.id),
        is_staff=bool(getattr(request.user, "is_staff", False)),
    )
