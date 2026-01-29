from datetime import datetime
from abc import ABC
from uuid import UUID
from shared_kernel.pubsub.domain.event_priority import EventPriority


class DomainEvent(ABC):
    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
        priority: EventPriority = EventPriority.MEDIUM,
    ) -> None:
        self.event_id = event_id
        self.occurred_on = occurred_on
        self.event_type = self.__class__.__name__
        self.priority = priority
