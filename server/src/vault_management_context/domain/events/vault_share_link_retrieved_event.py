from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class VaultShareLinkRetrievedEvent(DomainEvent):
    def __init__(
        self,
        setup_id: str,
        share_index: int,
        reopened: bool = False,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.setup_id = setup_id
        self.share_index = share_index
        self.reopened = reopened
