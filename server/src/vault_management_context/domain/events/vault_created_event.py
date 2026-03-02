from datetime import datetime, timezone
from uuid import UUID, uuid4
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class VaultCreatedEvent(DomainEvent):
    def __init__(
        self,
        setup_id: str,
        nb_shares: int,
        threshold: int,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(timezone.utc),
            priority=EventPriority.HIGH,
        )
        self.setup_id = setup_id
        self.nb_shares = nb_shares
        self.threshold = threshold
