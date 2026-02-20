from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class PermissionsTable(SQLModel, table=True):
    __tablename__: str = "Permission"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    group_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    permission: str = Field(default="Password")


class OwnershipTable(SQLModel, table=True):
    __tablename__: str = "Ownership"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    group_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    resource_type: str = Field(default="Password")
