from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, select

from identity_access_management_context.adapters.secondary.sql.model.iam_event import (
    IamEventTable,
)
from identity_access_management_context.application.gateways import (
    ServiceAccountCreationFacts,
    ServiceAccountEventRepository,
)
from identity_access_management_context.domain.events import ServiceAccountCreatedEvent
from identity_access_management_context.domain.events.service_account import ServiceAccountEvent
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc

_CREATED_EVENT_TYPE = ServiceAccountCreatedEvent.__name__

_NO_CREATION_FACTS = ServiceAccountCreationFacts(created_at=None, created_by_user_id=None)


class SqlServiceAccountEventRepository(SQLBaseRepository, ServiceAccountEventRepository):
    """Service-account audit events, stored as IamEvent rows.

    Separate from SqlIamEventRepository because this one also reads: a listing
    takes each account's creation date and creator from its creation event.
    """

    def __init__(self, session: Session):
        super().__init__(session)

    def extend(self, events: Sequence[ServiceAccountEvent]) -> None:
        rows = [
            IamEventTable(
                event_id=event.event_id,
                event_type=event.event_type,
                # Read back as a creation date, so normalised here rather than left to the driver.
                occurred_on=to_naive_utc(event.occurred_on),
                actor_user_id=event.user_id,
                event_data=event.event_data,
            )
            for event in events
        ]
        self._session.add_all(rows)
        self.commit()

    def get_creation_facts(self, service_account_ids: Sequence[UUID]) -> Sequence[ServiceAccountCreationFacts]:
        if not service_account_ids:
            return []

        # SQLAlchemy spells JSON access per dialect: JSON_EXTRACT on SQLite, ->> on PostgreSQL.
        account_id_column = IamEventTable.event_data["service_account_id"].as_string()  # type: ignore[index]
        wanted_ids = [str(account_id) for account_id in service_account_ids]

        # event_type is indexed, so it narrows to creation events before any JSON is read.
        query = select(
            IamEventTable.event_data,
            IamEventTable.occurred_on,
            IamEventTable.actor_user_id,
        ).where(
            IamEventTable.event_type == _CREATED_EVENT_TYPE,
            account_id_column.in_(wanted_ids),
        )
        rows = self._session.exec(query).all()

        facts_by_account: dict[str, ServiceAccountCreationFacts] = {}
        for event_data, occurred_on, actor_user_id in rows:
            facts = ServiceAccountCreationFacts(
                created_at=as_utc(occurred_on),
                created_by_user_id=actor_user_id,
            )
            facts_by_account[event_data["service_account_id"]] = facts

        # One slot per requested id, empty where no creation event was found.
        ordered_facts = []
        for account_id in service_account_ids:
            ordered_facts.append(facts_by_account.get(str(account_id), _NO_CREATION_FACTS))

        return ordered_facts
