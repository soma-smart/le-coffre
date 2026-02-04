from datetime import datetime
from uuid import UUID

from audit_logging_context.application.gateways import StoredEvent
from shared_kernel.domain.entities import DomainEvent


class InMemoryStoredEvent:
    """Implementation of StoredEvent for in-memory domain events"""

    def __init__(self, event: DomainEvent):
        self.event_id = event.event_id
        self.event_type = event.event_type
        self.occurred_on = event.occurred_on
        self.priority = event.priority
        # Convert event attributes to event_data dict
        self.event_data = {
            key: str(value)
            if not isinstance(value, (str, int, float, bool, type(None)))
            else value
            for key, value in event.__dict__.items()
        }
        # Extract metadata if available
        self.bounded_context = getattr(event, "bounded_context", None)
        self.actor_user_id = getattr(event, "actor_user_id", None)
        self.target_entity_id = getattr(event, "target_entity_id", None)
        self.target_entity_type = getattr(event, "target_entity_type", None)


class InMemoryEventRepository:
    def __init__(self):
        self.events: list[DomainEvent] = []

    def append_event(self, event: DomainEvent) -> None:
        self.events.append(event)

    def list_events(
        self,
        event_types: list[str] | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[StoredEvent]:
        filtered_events = self.events

        if event_types:
            filtered_events = [
                event for event in filtered_events if event.event_type in event_types
            ]

        if user_id:
            # Filter by actor_user_id if event has this property
            filtered_events = [
                event
                for event in filtered_events
                if getattr(event, "actor_user_id", None) == user_id
            ]

        if start_date:
            filtered_events = [
                event for event in filtered_events if event.occurred_on >= start_date
            ]

        if end_date:
            filtered_events = [
                event for event in filtered_events if event.occurred_on <= end_date
            ]

        return [InMemoryStoredEvent(event) for event in filtered_events]
