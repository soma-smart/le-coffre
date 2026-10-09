from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ExtensionPairingDeniedEvent(DomainEvent):
    """A user denied a browser-extension pairing request."""

    def __init__(
        self,
        user_id: UUID,
        pairing_id: UUID,
        device_name: str,
        created_from_ip: str | None = None,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.user_id = user_id
        self.pairing_id = pairing_id
        self.device_name = device_name
        self.created_from_ip = created_from_ip
