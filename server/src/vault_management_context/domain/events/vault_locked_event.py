from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class VaultLockedEvent(DomainEvent):
    def __init__(
        self,
        locked_by_user_id: UUID | None,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        # None when no one locked it: the server restarted, and the decrypted key
        # only ever lives in memory.
        self.locked_by_user_id = locked_by_user_id
