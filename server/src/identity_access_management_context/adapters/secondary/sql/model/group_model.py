from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class GroupTable(SQLModel, table=True):
    __tablename__: str = "Group"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    name: str = Field(nullable=False)
    is_personal: bool = Field(nullable=False, default=False)
    user_id: UUID | None = Field(nullable=True, default=None, index=True)
