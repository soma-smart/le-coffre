from datetime import datetime
from typing import Any
from uuid import UUID

from vault_management_context.domain.value_objects import StoredVaultEvent


class FakeVaultEventRepository:
    """Fake implementation of VaultEventRepository for testing"""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self._should_fail = False
        self.error: Exception | None = None

    def fail_next_append(self) -> None:
        """The next append_event() call raises once, instead of storing anything."""
        self._should_fail = True

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        """Append a vault event to storage"""
        if self._should_fail:
            self._should_fail = False
            raise RuntimeError("simulated database failure")
        if self.error is not None:
            raise self.error
        self.events.append(
            {
                "event_id": event_id,
                "event_type": event_type,
                "occurred_on": occurred_on,
                "actor_user_id": actor_user_id,
                "event_data": event_data,
            }
        )

    def get_last_event_type(self, event_types: list[str]) -> str | None:
        matching = [e for e in self.events if e["event_type"] in event_types]
        if not matching:
            return None
        return max(matching, key=lambda e: e["occurred_on"])["event_type"]

    def list_events(self, event_types: list[str]) -> list[StoredVaultEvent]:
        matching = sorted((e for e in self.events if e["event_type"] in event_types), key=lambda e: e["occurred_on"])
        return [
            StoredVaultEvent(event_type=e["event_type"], occurred_on=e["occurred_on"], event_data=dict(e["event_data"]))
            for e in matching
        ]
