from sqlmodel import SQLModel, Field
from uuid import UUID


class PermissionsTable(SQLModel, table=True):
    __tablename__: str = "PermissionsTable"

    id: UUID = Field(default_factory=UUID, nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    permission: str = Field(default="Password")


class OwnershipTable(SQLModel, table=True):
    __tablename__: str = "OwnershipTable"

    id: UUID = Field(default_factory=UUID, nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False)
    resource_id: UUID = Field(nullable=False)
    resource_type: str = Field(default="Password")


def create_permissions_tables(engine):
    SQLModel.metadata.create_all(engine)
