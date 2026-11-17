from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.events.service_account._event import ServiceAccountEvent


@dataclass(frozen=True)
class ServiceAccountLifecycleFacts:
    """When a service account was created and by whom, and when its token last rotated.

    These are not columns on the account: they are read back from its
    ``ServiceAccountCreatedEvent`` and ``ServiceAccountTokenRotatedEvent``, which
    are the system of record for them.
    """

    created_at: datetime | None
    created_by_principal_id: UUID | None
    last_rotated_at: datetime | None


class ServiceAccountEventRepository(Protocol):
    """Repository for service-account IAM audit events.

    Unlike the other IAM event ports this one also reads, because the creation
    and rotation events are where a listing gets its creation date, creator and
    last rotation.
    """

    def extend(self, events: Sequence[ServiceAccountEvent]) -> None:
        """Append service account events to storage.

        Takes the events themselves rather than pre-built rows: each one knows
        its own actor and payload, so the stored shape is decided in one place
        per event instead of at every call site.
        """

    def get_lifecycle_facts(self, service_account_ids: Sequence[UUID]) -> Sequence[ServiceAccountLifecycleFacts]:
        """Return lifecycle facts for these accounts, in order."""
