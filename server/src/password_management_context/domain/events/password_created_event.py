from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordCreatedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        owner_group_id: UUID,
        created_by_user_id: UUID,
        folder: str | None = None,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
        )
        self.password_id = password_id
        self.password_name = password_name
        self.owner_group_id = owner_group_id
        self.created_by_user_id = created_by_user_id
        self.folder = folder
