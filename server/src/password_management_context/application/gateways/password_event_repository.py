from datetime import datetime
from typing import Protocol
from uuid import UUID


class PasswordEventRepository(Protocol):
    """Repository for password audit events"""

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        password_id: UUID,
        actor_user_id: UUID,
        event_data: dict,
    ) -> None:
        """Append a password event to storage"""
        ...

    def list_events(
        self,
        password_id: UUID,
        actor_user_id: UUID | None = None,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """List events for a specific password with filters

        Returns list of dicts with keys: event_id, event_type, occurred_on,
        password_id, actor_user_id, event_data
        """
        ...

    def list_events_bulk(
        self,
        password_ids: list[UUID],
        event_types: list[str] | None = None,
    ) -> list[dict]:
        """List events for multiple passwords with optional event type filter

        Returns list of dicts with keys: event_id, event_type, occurred_on,
        password_id, actor_user_id, event_data
        Sorted by occurred_on descending (most recent first) per password
        """
        ...

    def list_events_by_actor(
        self,
        actor_user_id: UUID,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """List all password events performed by a given actor across all passwords.

        Returns list of dicts with keys: event_id, event_type, occurred_on,
        password_id, actor_user_id, event_data
        Sorted by occurred_on descending (most recent first).
        """
        ...
