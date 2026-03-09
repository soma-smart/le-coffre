from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class PasswordTable(SQLModel, table=True):
    __tablename__: str = "Password"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    name: str = Field(description="Password name")
    encrypted_value: str = Field(description="encrypted Password")
    folder: str | None = Field(description="Path to folder")
    login: str | None = Field(description="Login matching the password")
    url: str | None = Field(description="URL matching the password")
