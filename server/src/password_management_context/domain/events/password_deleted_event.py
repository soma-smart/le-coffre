from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordDeletedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        deleted_by_user_id: UUID,
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
        self.deleted_by_user_id = deleted_by_user_id
        self.owner_group_id = owner_group_id
        self.priority = "HIGH"  # DELETE - CRUD operation
