from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordUnsharedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        unshared_from_group_id: UUID,
        unshared_by_user_id: UUID,
        owner_group_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
        )
        self.password_id = password_id
        self.password_name = password_name
        self.unshared_from_group_id = unshared_from_group_id
        self.unshared_by_user_id = unshared_by_user_id
        self.owner_group_id = owner_group_id
        self.priority = "MEDIUM"  # Permission management
