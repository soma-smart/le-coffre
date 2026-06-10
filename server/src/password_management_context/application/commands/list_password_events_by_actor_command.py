from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from shared_kernel.domain.entities import AuthenticatedUser


@dataclass
class ListPasswordEventsByActorCommand:
    """List every password event performed by a given actor (admin-only)."""

    actor_user_id: UUID
    requesting_user: AuthenticatedUser
    event_types: list[str] | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
