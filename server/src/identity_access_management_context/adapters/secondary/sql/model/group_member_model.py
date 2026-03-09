from uuid import UUID

from sqlmodel import Field, SQLModel


class GroupMemberTable(SQLModel, table=True):
    __tablename__: str = "GroupMember"

    group_id: UUID = Field(nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False, primary_key=True, index=True)
    is_owner: bool = Field(nullable=False, default=False)
