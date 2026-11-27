from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, func, select

from identity_access_management_context.adapters.secondary.sql.model.iam_event import (
    IamEventTable,
)
from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountLifecycleFacts,
)
from identity_access_management_context.domain.events import (
    ServiceAccountCreatedEvent,
    ServiceAccountTokenRotatedEvent,
)
from identity_access_management_context.domain.events.service_account import ServiceAccountEvent
from shared_kernel.adapters.secondary.sql import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc

_CREATED_EVENT_TYPE = ServiceAccountCreatedEvent.__name__
_TOKEN_ROTATED_EVENT_TYPE = ServiceAccountTokenRotatedEvent.__name__


class SqlServiceAccountEventRepository(SQLBaseRepository, ServiceAccountEventRepository):
    """Service-account audit events, stored as IamEvent rows.

    Separate from SqlIamEventRepository because this one also reads: a listing
    takes each account's creation date and creator from its creation event, and
    its last rotation from its rotation events.
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
                actor_principal_id=event.actor_principal_id,
                event_data=event.event_data,
            )
            for event in events
        ]
        self._session.add_all(rows)
        self.commit()

    def get_lifecycle_facts(self, service_account_ids: Sequence[UUID]) -> Sequence[ServiceAccountLifecycleFacts]:
        if not service_account_ids:
            return []

        # SQLAlchemy spells JSON access per dialect: JSON_EXTRACT on SQLite, ->> on PostgreSQL.
        account_id_column = IamEventTable.event_data["service_account_id"].as_string()  # type: ignore[index]
        is_wanted = account_id_column.in_([str(account_id) for account_id in service_account_ids])

        # event_type is indexed, so it narrows to one kind of event before any JSON is read.
        created = {
            account_id: (occurred_on, actor_principal_id)
            for account_id, occurred_on, actor_principal_id in self._session.exec(
                select(account_id_column, IamEventTable.occurred_on, IamEventTable.actor_principal_id).where(
                    IamEventTable.event_type == _CREATED_EVENT_TYPE, is_wanted
                )
            ).all()
        }
        last_rotated = dict(
            self._session.exec(
                select(account_id_column, func.max(IamEventTable.occurred_on))
                .where(IamEventTable.event_type == _TOKEN_ROTATED_EVENT_TYPE, is_wanted)
                .group_by(account_id_column)
            ).all()
        )

        # One slot per requested id, empty where no event was found.
        ordered_facts = []
        for account_id in map(str, service_account_ids):
            created_at, created_by = created.get(account_id, (None, None))
            ordered_facts.append(
                ServiceAccountLifecycleFacts(
                    created_at=as_utc(created_at),
                    created_by_principal_id=created_by,
                    last_rotated_at=as_utc(last_rotated.get(account_id)),
                )
            )

        return ordered_facts
