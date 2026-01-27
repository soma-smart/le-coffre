from typing import Optional
from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4


class PasswordTable(SQLModel, table=True):
    __tablename__: str = "PasswordTable"

    id: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, index=True
    )
    name: str = Field(description="Password name")
    encrypted_value: str = Field(description="encrypted Password")
    folder: Optional[str] = Field(description="Path to folder")
