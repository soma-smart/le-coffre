from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.pubsub import DomainEvent


class PasswordAccessCheckedEvent(DomainEvent):
    """Event emitted when access to a password is checked"""

    def __init__(
        self,
        password_id: UUID,
        checked_by_user_id: UUID,
        has_access: bool,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
        )
        self.password_id = password_id
        self.checked_by_user_id = checked_by_user_id
        self.has_access = has_access
        self.priority = "LOW"  # Technical check, not CRUD
