from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from identity_access_management_context.domain.events.service_account._event import ServiceAccountEvent


@dataclass(frozen=True)
class ServiceAccountCreationFacts:
    """When a service account was created, and by whom.

    These are not columns on the account: they are read back from its
    ``ServiceAccountCreatedEvent``, which is the system of record for them.
    """

    created_at: datetime | None
    created_by_user_id: UUID | None


class ServiceAccountEventRepository(ABC):
    """Repository for service-account IAM audit events.

    Unlike the other IAM event ports this one also reads, because the creation
    event is where a listing gets its creation date and creator.
    """

    @abstractmethod
    def extend(self, events: Sequence[ServiceAccountEvent]) -> None:
        """Append service account events to storage.

        Takes the events themselves rather than pre-built rows: each one knows
        its own actor and payload, so the stored shape is decided in one place
        per event instead of at every call site.
        """

    @abstractmethod
    def get_creation_facts(self, service_account_ids: Sequence[UUID]) -> Sequence[ServiceAccountCreationFacts]:
        """Return creation facts for these accounts, in order."""
