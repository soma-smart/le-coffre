"""Base classes for all service-account domain events"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects.event_priority import EventPriority


@dataclass(init=False)  # TODO: Remove the `init` flag when `DomainEvent` is a dataclass
class ServiceAccountEvent(DomainEvent, ABC):
    """A service-account event."""

    actor_principal_id: UUID
    """The principal who fired the event."""

    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
        actor_principal_id: UUID,
        priority: EventPriority = EventPriority.MEDIUM,
    ) -> None:
        super().__init__(event_id, occurred_on, priority)
        self.actor_principal_id = actor_principal_id

    def _make_event_data(self) -> dict[str, str]:
        return {"actor_principal_id": str(self.actor_principal_id)}

    @property
    def event_data(self) -> dict[str, str]:
        """Convert event to storage-ready dictionary."""
        return self._make_event_data()


@dataclass(init=False)
class ServiceAccountItemEvent(ServiceAccountEvent, ABC):
    """A service-account event concerning one identified account."""

    service_account_id: UUID
    """ID of the service account."""

    service_account_name: str
    """Name of the service account."""

    group_id: UUID
    """ID of the group the account belongs to: what files the event in that group's history."""

    group_name: str
    """Name of that group when the event happened, still readable once the group is deleted."""

    def __init__(
        self,
        event_id: UUID,
        occurred_on: datetime,
        actor_principal_id: UUID,
        service_account_id: UUID,
        service_account_name: str,
        group_id: UUID,
        group_name: str,
        priority: EventPriority = EventPriority.MEDIUM,
    ) -> None:
        super().__init__(event_id, occurred_on, actor_principal_id, priority)
        self.service_account_id = service_account_id
        self.service_account_name = service_account_name
        self.group_id = group_id
        self.group_name = group_name

    def _make_event_data(self) -> dict[str, str]:
        return super()._make_event_data() | {
            "service_account_id": str(self.service_account_id),
            "service_account_name": self.service_account_name,
            "group_id": str(self.group_id),
            "group_name": self.group_name,
        }
