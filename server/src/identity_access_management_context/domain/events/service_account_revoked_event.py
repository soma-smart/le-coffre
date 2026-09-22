from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ServiceAccountRevokedEvent(DomainEvent):
    """A service account was revoked, by its group's manager or by the group's deletion.

    The account row survives so the revocation stays auditable; this event records
    who ordered it.
    """

    def __init__(
        self,
        group_id: UUID,
        service_account_id: UUID,
        service_account_name: str,
        revoked_by_user_id: UUID,
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
        self.revoked_by_user_id = revoked_by_user_id
