from sqlmodel import Session, select, col
from datetime import datetime
from uuid import UUID
import json

from audit_logging_context.application.gateways import EventRepository
from audit_logging_context.adapters.secondary.sql.model.domain_event_model import (
    DomainEventTable,
)
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class StoredDomainEvent(DomainEvent):
    """Wrapper for domain events retrieved from storage"""

    def __init__(
        self,
        event_id: UUID,
        event_type: str,
        occurred_on: datetime,
        priority: EventPriority,
        event_data: dict,
    ):
        super().__init__(event_id=event_id, occurred_on=occurred_on, priority=priority)
        self.event_type = event_type
        self.event_data = event_data


class SqlEventRepository(EventRepository):
    def __init__(self, session: Session):
        self._session = session

    def append_event(self, event: DomainEvent) -> None:
        """Save a domain event by serializing it to JSON"""
        # Serialize all event attributes to JSON
        event_dict = {
            key: str(value)
            if not isinstance(value, (str, int, float, bool, type(None)))
            else value
            for key, value in event.__dict__.items()
        }

        db_event = DomainEventTable(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_on=event.occurred_on,
            priority=event.priority.value,
            event_data=json.dumps(event_dict),
        )
        self._session.add(db_event)
        self._session.commit()
        self._session.refresh(db_event)

    def list_events(
        self,
        event_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[DomainEvent]:
        """Retrieve all stored domain events, optionally filtered by event types and date range"""
        statement = select(DomainEventTable).order_by(col(DomainEventTable.occurred_on))

        # Apply event_type filter if provided
        if event_types:
            statement = statement.where(
                col(DomainEventTable.event_type).in_(event_types)
            )

        # Apply date range filters if provided
        if start_date:
            statement = statement.where(col(DomainEventTable.occurred_on) >= start_date)
        if end_date:
            statement = statement.where(col(DomainEventTable.occurred_on) <= end_date)

        results = self._session.exec(statement).all()

        events = []
        for db_event in results:
            event_data = json.loads(db_event.event_data)
            stored_event = StoredDomainEvent(
                event_id=db_event.event_id,
                event_type=db_event.event_type,
                occurred_on=db_event.occurred_on,
                priority=EventPriority(db_event.priority),
                event_data=event_data,
            )
            events.append(stored_event)

        return events
