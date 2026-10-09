from datetime import datetime
from typing import Any
from uuid import UUID


class FakeAdminEventRepository:
    """Fake implementation of AdminEventRepository for testing"""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.raise_on_append = False

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        if self.raise_on_append:
            raise RuntimeError("simulated audit storage failure")
        self.events.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_on": occurred_on,
                "actor_user_id": actor_user_id,
                "event_data": event_data,
            }
        )
