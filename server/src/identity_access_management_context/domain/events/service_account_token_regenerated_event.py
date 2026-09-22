from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ServiceAccountTokenRegeneratedEvent(DomainEvent):
    """A service account's token was replaced, retiring the previous one.

    The account keeps its id, name, group and creation event, so the sequence of
    these events is the account's rotation history.
    """

    def __init__(
        self,
        group_id: UUID,
        service_account_id: UUID,
        service_account_name: str,
        regenerated_by_user_id: UUID,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.group_id = group_id
        self.service_account_id = service_account_id
        self.service_account_name = service_account_name
        self.regenerated_by_user_id = regenerated_by_user_id
