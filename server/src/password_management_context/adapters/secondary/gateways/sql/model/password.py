from typing import Optional
from sqlmodel import CheckConstraint, SQLModel, Field
from uuid import UUID


class PasswordTable(SQLModel, table=True):
    __tablename__ = "PasswordTable"

    id: UUID = Field(default_factory=UUID, nullable=False, primary_key=True, index=True)
    name: str = Field(description="Password name")
    encrypted_value: str = Field(description="encrypted Password")
    folder: Optional[str] = Field(description="Path to folder")


def create_password_table(engine):
    SQLModel.metadata.create_all(engine)
    