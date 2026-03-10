from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class UserDeletedEvent(DomainEvent):
    def __init__(
        self,
        user_id: UUID,
        deleted_by_user_id: UUID,
        personal_group_id: UUID | None,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.user_id = user_id
        self.deleted_by_user_id = deleted_by_user_id
        self.personal_group_id = personal_group_id
