from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class PermissionsTable(SQLModel, table=True):
    __tablename__: str = "Permission"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    group_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    permission: str = Field(default="Password")
    # NULL means the share is permanent, which is what every row predating
    # temporary sharing is. Stored naive UTC like every other timestamp here:
    # go through shared_kernel.adapters.secondary.sql.naive_utc to read or write it.
    expires_at: datetime | None = Field(default=None, nullable=True, index=True)


class OwnershipTable(SQLModel, table=True):
    __tablename__: str = "Ownership"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    group_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    resource_type: str = Field(default="Password")
