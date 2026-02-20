from datetime import datetime
from uuid import UUID
from sqlmodel import Field, SQLModel, JSON, Column


class IamEventTable(SQLModel, table=True):
    """SQLModel table for IAM audit events"""

    __tablename__: str = "IamEvent"

    event_id: UUID = Field(primary_key=True)
    event_type: str = Field(index=True)
    occurred_on: datetime = Field(index=True)
    actor_user_id: UUID | None = Field(default=None, index=True)
    event_data: dict = Field(default_factory=dict, sa_column=Column(JSON))
