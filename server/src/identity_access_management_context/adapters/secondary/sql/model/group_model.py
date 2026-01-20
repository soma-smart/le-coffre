from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class GroupTable(SQLModel, table=True):
    __tablename__: str = "GroupTable"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    name: str = Field(nullable=False)
    is_personal: bool = Field(nullable=False, default=False)
    user_id: UUID | None = Field(nullable=True, default=None, index=True)


def create_group_table(engine):
    SQLModel.metadata.create_all(engine)
