from datetime import datetime
from typing import Any
from uuid import UUID


class FakeGroupEventRepository:
    """Fake implementation of GroupEventRepository for testing"""

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        self.events.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_on": occurred_on,
                "actor_user_id": actor_user_id,
                "event_data": event_data,
            }
        )

    def list_events(
        self,
        group_id: UUID,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """List membership events for a specific group with optional filters"""
        group_id_str = str(group_id)
        filtered = [event for event in self.events if event["event_data"].get("group_id") == group_id_str]

        if event_types:
            filtered = [event for event in filtered if event["event_type"] in event_types]

        if start_date:
            filtered = [event for event in filtered if event["occurred_on"] >= start_date]

        if end_date:
            filtered = [event for event in filtered if event["occurred_on"] <= end_date]

        filtered = sorted(filtered, key=lambda e: e["occurred_on"], reverse=True)

        return [
            {
                "event_id": str(event["event_id"]),
                "event_type": event["event_type"],
                "occurred_on": event["occurred_on"].isoformat(),
                "actor_user_id": str(event["actor_user_id"]),
                "event_data": event["event_data"],
            }
            for event in filtered
        ]
