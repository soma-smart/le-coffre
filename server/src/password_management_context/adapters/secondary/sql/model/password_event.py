from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel, JSON, Column


class PasswordEventTable(SQLModel, table=True):
    """SQLModel table for password audit events"""

    __tablename__: str = "password_events"

    event_id: UUID = Field(primary_key=True)
    event_type: str = Field(index=True)
    occurred_on: datetime = Field(index=True)
    password_id: UUID = Field(index=True)
    actor_user_id: UUID = Field(index=True)
    event_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
