from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AuthSessionTable(SQLModel, table=True):
    __tablename__: str = "AuthSession"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False, index=True)
    current_refresh_token_jti: str = Field(nullable=False, unique=True, index=True)
    created_at: datetime = Field(nullable=False)
    updated_at: datetime = Field(nullable=False)
    invalidated_at: datetime | None = Field(default=None, nullable=True, index=True)
