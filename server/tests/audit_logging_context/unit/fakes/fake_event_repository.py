from datetime import datetime

from shared_kernel.domain.entities import DomainEvent


class FakeEventRepository:
    def __init__(self):
        self.events: list[DomainEvent] = []

    def append_event(self, event: DomainEvent) -> None:
        self.events.append(event)

    def list_events(
        self,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DomainEvent]:
        filtered_events = self.events

        if event_types:
            filtered_events = [
                event for event in filtered_events if event.event_type in event_types
            ]

        if start_date:
            filtered_events = [
                event for event in filtered_events if event.occurred_on >= start_date
            ]

        if end_date:
            filtered_events = [
                event for event in filtered_events if event.occurred_on <= end_date
            ]

        return filtered_events
