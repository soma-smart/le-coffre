from datetime import datetime
from typing import Protocol

from shared_kernel.domain.entities import DomainEvent


class EventRepository(Protocol):
    def append_event(self, event: DomainEvent) -> None: ...
    def list_events(
        self,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DomainEvent]: ...
