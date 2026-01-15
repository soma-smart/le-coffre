from uuid import UUID

from sqlmodel import Field, SQLModel


class PermissionsTable(SQLModel, table=True):
    __tablename__: str = "PermissionsTable"

    id: int = Field(default=None, primary_key=True)
    user_id: UUID = Field(nullable=False, index=True)
    resource_id: UUID = Field(nullable=False, index=True)
    permission: str = Field(nullable=False)


class OwnershipsTable(SQLModel, table=True):
    __tablename__: str = "OwnershipsTable"

    id: int = Field(default=None, primary_key=True)
    user_id: UUID = Field(nullable=False, index=True)
    resource_id: UUID = Field(nullable=False, index=True)


def create_rights_tables(engine):
    SQLModel.metadata.create_all(engine)
