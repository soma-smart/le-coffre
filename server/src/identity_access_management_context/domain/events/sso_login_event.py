from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class SsoLoginEvent(DomainEvent):
    def __init__(
        self,
        user_id: UUID,
        email: str,
        is_new_user: bool,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.MEDIUM,
        )
        self.user_id = user_id
        self.email = email
        self.is_new_user = is_new_user
