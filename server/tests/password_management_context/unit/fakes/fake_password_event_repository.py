from datetime import datetime
from typing import Any
from uuid import UUID


class FakePasswordEventRepository:
    """Fake implementation of PasswordEventRepository for testing"""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

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
        self.events.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_on": occurred_on,
                "password_id": password_id,
                "actor_user_id": actor_user_id,
                "event_data": event_data,
            }
        )

    def list_events(
        self,
        password_id: UUID,
        actor_user_id: UUID | None = None,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """List events for a specific password with filters"""
        filtered = [event for event in self.events if event["password_id"] == password_id]

        if actor_user_id:
            filtered = [event for event in filtered if event["actor_user_id"] == actor_user_id]

        if event_types:
            filtered = [event for event in filtered if event["event_type"] in event_types]

        if start_date:
            filtered = [event for event in filtered if event["occurred_on"] >= start_date]

        if end_date:
            filtered = [event for event in filtered if event["occurred_on"] <= end_date]

        return sorted(filtered, key=lambda e: e["occurred_on"], reverse=True)

    def list_events_bulk(
        self,
        password_ids: list[UUID],
        event_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List events for multiple passwords with optional event type filter"""
        filtered = [event for event in self.events if event["password_id"] in password_ids]

        if event_types:
            filtered = [event for event in filtered if event["event_type"] in event_types]

        return sorted(filtered, key=lambda e: e["occurred_on"], reverse=True)
