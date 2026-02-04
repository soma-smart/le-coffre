from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from shared_kernel.domain.value_objects import EventPriority


@dataclass(frozen=True)
class EventDTO:
    """Data Transfer Object for audit events with extracted user information"""

    event_id: UUID
    event_type: str
    occurred_on: datetime
    priority: EventPriority
    user_id: UUID | None


@dataclass(frozen=True)
class ListEventResponse:
    events: list[EventDTO]
