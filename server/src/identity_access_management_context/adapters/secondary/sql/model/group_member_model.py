from sqlmodel import SQLModel, Field
from uuid import UUID


class GroupMemberTable(SQLModel, table=True):
    __tablename__: str = "GroupMemberTable"

    group_id: UUID = Field(nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False, primary_key=True, index=True)
    is_owner: bool = Field(nullable=False, default=False)


def create_group_member_table(engine):
    SQLModel.metadata.create_all(engine)
