from datetime import datetime, timezone
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class AdminPromotedEvent(DomainEvent):
    def __init__(
        self,
        user_id: UUID,
        promoted_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(timezone.utc),
            priority=EventPriority.HIGH,
        )
        self.user_id = user_id
        self.promoted_by_user_id = promoted_by_user_id
