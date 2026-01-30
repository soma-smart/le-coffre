from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class UserPasswordTable(SQLModel, table=True):
    __tablename__: str = "UserPasswordTable"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    email: str = Field(description="User email", nullable=False)
    password_hash: str = Field(description="Hashed user password", nullable=False)
    display_name: str = Field(description="User display name", nullable=False)
