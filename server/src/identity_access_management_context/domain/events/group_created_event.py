from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class GroupCreatedEvent(DomainEvent):
    def __init__(
        self,
        group_id: UUID,
        group_name: str,
        created_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.group_id = group_id
        self.group_name = group_name
        self.created_by_user_id = created_by_user_id
