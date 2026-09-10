from datetime import datetime
from typing import Protocol
from uuid import UUID


class GroupEventRepository(Protocol):
    """Repository for group-related IAM audit events"""

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        """Append a group event to storage"""
        ...

    def list_events(
        self,
        group_id: UUID,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """List membership events for a specific group with optional filters"""
        ...
