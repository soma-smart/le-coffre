from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class RevokedTokenTable(SQLModel, table=True):
    __tablename__: str = "RevokedToken"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    jti: str = Field(nullable=False, unique=True, index=True)
    user_id: UUID | None = Field(default=None, nullable=True, index=True)
    token_type: str = Field(nullable=False)
    expires_at: datetime | None = Field(default=None, nullable=True, index=True)
    revoked_at: datetime = Field(nullable=False)
    reason: str = Field(nullable=False)
