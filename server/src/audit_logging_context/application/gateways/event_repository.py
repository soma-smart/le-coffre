from datetime import datetime
from typing import Protocol
from uuid import UUID

from shared_kernel.domain.entities import DomainEvent
from audit_logging_context.application.gateways.stored_event import StoredEvent


class EventRepository(Protocol):
    def append_event(self, event: DomainEvent) -> None: ...
    def list_events(
        self,
        event_types: list[str] | None = None,
        user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[StoredEvent]: ...
