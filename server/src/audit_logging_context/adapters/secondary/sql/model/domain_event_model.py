from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Column, Text


class DomainEventTable(SQLModel, table=True):
    __tablename__: str = "DomainEventTable"

    event_id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    event_type: str = Field(description="Type/class name of the domain event")
    occurred_on: datetime = Field(description="Timestamp when event occurred")
    priority: str = Field(description="Event priority level (HIGH, MEDIUM, LOW)")
    event_data: str = Field(
        sa_column=Column(Text), description="JSON serialized event data"
    )

    # Filtering columns for efficient queries
    bounded_context: str | None = Field(
        default=None, description="Bounded context that produced the event"
    )
    actor_user_id: UUID | None = Field(
        default=None, description="User who performed the action"
    )
    target_entity_id: UUID | None = Field(
        default=None, description="Entity that was affected by the action"
    )
    target_entity_type: str | None = Field(
        default=None,
        description="Type of the target entity (password, group, user, etc.)",
    )
