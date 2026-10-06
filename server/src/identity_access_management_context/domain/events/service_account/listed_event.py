from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from shared_kernel.domain.value_objects.event_priority import EventPriority

from ._event import ServiceAccountEvent


@dataclass(init=False)
class ServiceAccountsListedEvent(ServiceAccountEvent):
    """A group's service accounts were read.

    Scoped to the group rather than to one account, since a listing concerns all
    of them. Filed at LOW priority: it records a read, not a change.
    """

    group_id: UUID | None
    """ID of the group whose service accounts were listed, or None across every reachable group."""

    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
        user_id: UUID,
        group_id: UUID | None,
        priority: EventPriority = EventPriority.LOW,
    ) -> None:
        super().__init__(event_id, occurred_on, user_id, priority)
        self.group_id = group_id

    def _make_event_data(self) -> dict[str, str]:
        if self.group_id is None:
            return super()._make_event_data()
        return super()._make_event_data() | {"group_id": str(self.group_id)}
