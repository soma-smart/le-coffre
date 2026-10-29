from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class UserAddedToGroupEvent(DomainEvent):
    def __init__(
        self,
        group_id: UUID,
        user_id: UUID,
        added_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.MEDIUM,
        )
        self.group_id = group_id
        self.user_id = user_id
        self.added_by_user_id = added_by_user_id
