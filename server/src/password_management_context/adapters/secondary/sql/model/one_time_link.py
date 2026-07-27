from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class OneTimeLinkTable(SQLModel, table=True):
    """SQLModel table for single-use password links.

    Rows survive consumption and revocation so the read stays auditable; only
    the SHA-256 of the token is kept, never the token itself.
    """

    __tablename__: str = "OneTimeLink"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    password_id: UUID = Field(nullable=False, index=True)
    token_hash: str = Field(nullable=False, unique=True, index=True, description="SHA-256 hex of the link token")
    created_by_user_id: UUID = Field(nullable=False, index=True)
    created_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    read_at: datetime | None = Field(default=None, description="When the link was consumed")
    revoked_at: datetime | None = Field(default=None, description="When the owner revoked the link")
