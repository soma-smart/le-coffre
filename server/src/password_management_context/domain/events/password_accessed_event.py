from datetime import datetime
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class PasswordAccessedEvent(DomainEvent):
    def __init__(
        self,
        password_id: UUID,
        password_name: str,
        accessed_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.LOW,
        )
        self.password_id = password_id
        self.password_name = password_name
        self.accessed_by_user_id = accessed_by_user_id
