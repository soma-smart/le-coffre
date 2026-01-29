from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class PasswordSharedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        owner_group_id: UUID,
        shared_with_group_id: UUID,
        shared_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.password_id = password_id
        self.owner_group_id = owner_group_id
        self.shared_with_group_id = shared_with_group_id
        self.shared_by_user_id = shared_by_user_id
