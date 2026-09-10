from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlmodel import Session, select

from identity_access_management_context.adapters.secondary.sql.model.iam_event import (
    IamEventTable,
)
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository


class GroupMembershipEventType(Enum):
    """Group event types that make up a group's membership history.

    Values match the domain event class names stored as ``event_type`` in
    IamEvent rows (see identity_access_management_context.domain.events).
    """

    USER_ADDED = "UserAddedToGroupEvent"
    OWNER_ADDED = "OwnerAddedToGroupEvent"
    USER_REMOVED = "UserRemovedFromGroupEvent"


class SqlIamEventRepository(SQLBaseRepository):
    """SQL implementation of IAM event repository"""

    def __init__(self, session: Session):
        super().__init__(session)

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        actor_user_id: UUID | None,
        event_data: dict,
    ) -> None:
        """Append an IAM event to storage"""
        event = IamEventTable(
            event_id=event_id,
            event_type=event_type,
            occurred_on=occurred_on,
            actor_user_id=actor_user_id,
            event_data=event_data,
        )
        self._session.add(event)
        self.commit()

    def list_events(
        self,
        group_id: UUID,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """List membership events for a specific group with optional filters.

        IamEventTable is shared across the whole IAM context (users, groups,
        SSO, admin) and has no dedicated group_id column, so this narrows by
        event_type at the SQL level first, then filters on unstructured event_data
        in Python.
        """
        allowed_types = {member.value for member in GroupMembershipEventType}
        if event_types:
            allowed_types &= set(event_types)

        query = select(IamEventTable).where(IamEventTable.event_type.in_(allowed_types))  # type: ignore[attr-defined]

        if start_date:
            query = query.where(IamEventTable.occurred_on >= start_date)

        if end_date:
            query = query.where(IamEventTable.occurred_on <= end_date)

        query = query.order_by(IamEventTable.occurred_on.desc())  # type: ignore[attr-defined]

        results = self._session.exec(query).all()

        group_id_str = str(group_id)

        return [
            {
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "occurred_on": event.occurred_on.isoformat(),
                "actor_user_id": str(event.actor_user_id),
                "event_data": event.event_data,
            }
            for event in results
            if event.event_data.get("group_id") == group_id_str
        ]
