from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ExtensionPairedEvent(DomainEvent):
    """A browser extension was granted a read-only credential.

    HIGH priority like the login events: this is a new long-lived way into the
    account, and it is what an incident responder looks for when asking "when
    did this device gain access".
    """

    def __init__(
        self,
        user_id: UUID,
        token_id: UUID,
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
        self.token_id = token_id
        self.device_name = device_name
        self.created_from_ip = created_from_ip
