from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordAccessedEvent(DomainEvent):
    """Event emitted when a password is accessed/read by a user"""

    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        accessed_by_user_id: UUID,
        accessed_through_group_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
        )
        self.password_id = password_id
        self.password_name = password_name
        self.accessed_by_user_id = accessed_by_user_id
        self.accessed_through_group_id = accessed_through_group_id
        self.priority = "HIGH"  # CRUD operation
