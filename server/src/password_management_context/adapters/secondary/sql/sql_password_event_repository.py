from datetime import datetime
from uuid import UUID
from sqlmodel import Session, select

from password_management_context.adapters.secondary.sql.model.password_event import (
    PasswordEventTable,
)


class SqlPasswordEventRepository:
    """SQL implementation of password event repository"""

    def __init__(self, session: Session):
        self.session = session

    def append_event(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        password_id: UUID,
        actor_user_id: UUID,
        event_data: dict,
    ) -> None:
        """Append a password event to storage"""
        event = PasswordEventTable(
            event_id=event_id,
            event_type=event_type,
            occurred_on=occurred_on,
            password_id=password_id,
            actor_user_id=actor_user_id,
            event_data=event_data,
        )
        self.session.add(event)
        self.session.commit()

    def list_events(
        self,
        password_id: UUID,
        actor_user_id: UUID | None = None,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """List events for a specific password with filters"""
        query = select(PasswordEventTable).where(
            PasswordEventTable.password_id == password_id
        )

        if actor_user_id:
            query = query.where(PasswordEventTable.actor_user_id == actor_user_id)

        if event_types:
            query = query.where(PasswordEventTable.event_type.in_(event_types))  # type: ignore[attr-defined]

        if start_date:
            query = query.where(PasswordEventTable.occurred_on >= start_date)

        if end_date:
            query = query.where(PasswordEventTable.occurred_on <= end_date)

        query = query.order_by(PasswordEventTable.occurred_on.desc())  # type: ignore[attr-defined]

        results = self.session.exec(query).all()

        return [
            {
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "occurred_on": event.occurred_on.isoformat(),
                "password_id": str(event.password_id),
                "actor_user_id": str(event.actor_user_id),
                "event_data": event.event_data,
            }
            for event in results
        ]
