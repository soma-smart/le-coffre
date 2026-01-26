from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordsListedEvent(DomainEvent):
    """Event emitted when passwords are listed by a user"""

    def __init__(
        self,
        listed_by_user_id: UUID,
        folder: str | None = None,
        count: int = 0,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
        )
        self.listed_by_user_id = listed_by_user_id
        self.folder = folder
        self.count = count
        self.priority = "LOW"  # List operation, not CRUD
