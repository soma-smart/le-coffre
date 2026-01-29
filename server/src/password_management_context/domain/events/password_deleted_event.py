from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent, EventPriority


class PasswordDeletedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        deleted_by_user_id: UUID,
        owner_group_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.password_id = password_id
        self.deleted_by_user_id = deleted_by_user_id
        self.owner_group_id = owner_group_id
