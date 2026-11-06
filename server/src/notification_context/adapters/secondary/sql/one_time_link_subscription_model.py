from datetime import datetime
from uuid import UUID

from sqlmodel import DateTime, Field, SQLModel


class OneTimeLinkSubscriptionTable(SQLModel, table=True):
    __tablename__: str = "OneTimeLinkSubscription"

    # No foreign key to OneTimeLink nor User: bounded contexts do not share tables.
    # A row only lives until its link is read or has expired, so the table stays
    # as small as the set of links still waiting to be read.
    link_id: UUID = Field(primary_key=True)
    user_id: UUID = Field(nullable=False)
    expires_at: datetime = Field(sa_type=DateTime, nullable=False, index=True)
    notify_on_read: bool = Field(default=False, nullable=False)
    notify_on_expiry: bool = Field(default=False, nullable=False)
