from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ServiceAccountCreatedEvent(DomainEvent):
    """A service account was minted on a group.

    This event is the system of record for when the account was created and by
    whom: those two facts are not columns on the account itself. Callers must
    therefore pass `occurred_on` explicitly from the injected TimeGateway rather
    than letting it default to the wall clock.
    """

    def __init__(
        self,
        group_id: UUID,
        service_account_id: UUID,
        service_account_name: str,
        created_by_user_id: UUID,
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
        self.created_by_user_id = created_by_user_id
