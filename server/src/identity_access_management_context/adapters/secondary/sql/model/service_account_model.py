from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ServiceAccountTable(SQLModel, table=True):
    """Table for group-owned service accounts."""

    __tablename__: str = "ServiceAccount"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    group_id: UUID = Field(nullable=False, index=True)
    name: str = Field(nullable=False)
    token_hash: str = Field(
        nullable=False, unique=True, index=True, description="SHA-256 hex of the service account token"
    )
    revoked_at: datetime | None = Field(default=None, index=True, description="When the account was revoked")
