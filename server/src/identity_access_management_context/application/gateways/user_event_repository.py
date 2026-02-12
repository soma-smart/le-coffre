from datetime import datetime
from typing import Protocol
from uuid import UUID


class UserEventRepository(Protocol):
    """Repository for user-related IAM audit events"""

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        """Append a user event to storage"""
        ...
