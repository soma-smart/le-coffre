"""Base class for all service-account domain events"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects.event_priority import EventPriority


@dataclass(init=False)  # TODO: Remove the `init` flag when `DomainEvent` is a dataclass
class ServiceAccountEvent(DomainEvent, ABC):
    """A service-account event that knows how to become an audit row.

    Stays a DomainEvent, so it keeps the event_id, occurred_on and event_type
    that the audit row is built from, and can still go on the publisher bus like
    every other IAM event.

    What it adds is serialisation: the payload that reaches storage is defined
    here, next to the event, rather than assembled by each use case. That is
    deliberate for credentials — it leaves exactly one place per event where the
    stored payload is decided, so "the token and its hash never reach the audit
    log" is something you can read off three methods instead of auditing every
    call site.
    """

    user_id: UUID
    """The user who fired the event."""

    service_account_id: UUID
    """ID of the service account."""

    service_account_name: str
    """Name of the service account."""

    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
        user_id: UUID,
        service_account_id: UUID,
        service_account_name: str,
        priority: EventPriority = EventPriority.MEDIUM,
    ) -> None:
        super().__init__(event_id, occurred_on, priority)
        self.user_id = user_id
        self.service_account_id = service_account_id
        self.service_account_name = service_account_name

    def _make_event_data(self) -> dict[str, str]:
        return {
            "user_id": str(self.user_id),
            "service_account_id": str(self.service_account_id),
            "service_account_name": self.service_account_name,
        }

    @property
    def event_data(self) -> dict[str, str]:
        """Convert event to storage-ready dictionary."""
        return self._make_event_data()
