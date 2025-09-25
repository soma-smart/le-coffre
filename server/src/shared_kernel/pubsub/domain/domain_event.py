from datetime import datetime
from abc import ABC
from uuid import UUID


class DomainEvent(ABC):
    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
    ) -> None:
        self.event_id = event_id
        self.occurred_on = occurred_on
        self.event_type = self.__class__.__name__
