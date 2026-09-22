from collections.abc import Sequence
from typing import Any
from uuid import UUID

from identity_access_management_context.application.gateways import (
    ServiceAccountCreationFacts,
    ServiceAccountEventRepository,
)
from identity_access_management_context.domain.events import ServiceAccountCreatedEvent
from identity_access_management_context.domain.events.service_account import (
    ServiceAccountEvent,
    ServiceAccountItemEvent,
)


class FakeServiceAccountEventRepository(ServiceAccountEventRepository):
    """In-memory service account event repository for testing.

    Folds its own appended events like the SQL adapter folds IamEvent rows, so the
    tests exercise the real derivation rather than a lookup table.
    """

    def __init__(self):
        self.events: list[dict[str, Any]] = []

    def extend(self, events: Sequence[ServiceAccountEvent]) -> None:
        for event in events:
            self.events.append(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "occurred_on": event.occurred_on,
                    "actor_user_id": event.user_id,
                    "event_data": event.event_data,
                    # Only item events name an account; a listing is group-scoped.
                    "service_account_id": (
                        event.service_account_id if isinstance(event, ServiceAccountItemEvent) else None
                    ),
                    "is_creation": isinstance(event, ServiceAccountCreatedEvent),
                }
            )

    def get_creation_facts(self, service_account_ids: Sequence[UUID]) -> Sequence[ServiceAccountCreationFacts]:
        # One slot per requested id, empty where no creation event was found.
        by_account = {event["service_account_id"]: event for event in self.events if event["is_creation"]}
        facts = []
        for account_id in service_account_ids:
            event = by_account.get(account_id)
            facts.append(
                ServiceAccountCreationFacts(
                    created_at=event["occurred_on"] if event else None,
                    created_by_user_id=event["actor_user_id"] if event else None,
                )
            )
        return facts
