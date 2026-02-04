from datetime import datetime
from typing import Protocol
from uuid import UUID

from shared_kernel.domain.value_objects import EventPriority


class StoredEvent(Protocol):
    """
    Protocol for stored domain events retrieved from a repository.
    Represents the persisted form of events with serialized data and extracted metadata.
    """

    event_id: UUID
    event_type: str
    occurred_on: datetime
    priority: EventPriority
    event_data: dict  # Serialized event attributes

    # Extracted metadata for efficient filtering
    bounded_context: str | None
    actor_user_id: UUID | None
    target_entity_id: UUID | None
    target_entity_type: str | None
