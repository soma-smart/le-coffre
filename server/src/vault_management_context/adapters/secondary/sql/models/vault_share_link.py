from datetime import datetime
from uuid import UUID

from sqlmodel import DateTime, Field, SQLModel


class VaultShareLinkTable(SQLModel, table=True):
    """SQLModel table for the links distributing Shamir shares to their custodians.

    Only the SHA-256 of the link token is kept, and the share itself only in a
    form sealed under a key that exists solely in the link: this table cannot
    rebuild the master key, even together with the rest of the database. A row
    is deleted as soon as its link is retrieved or expires.
    """

    __tablename__: str = "VaultShareLink"

    id: UUID = Field(primary_key=True, nullable=False)
    setup_id: str = Field(nullable=False, index=True)
    share_index: int = Field(nullable=False)
    lookup_hash: str = Field(nullable=False, unique=True, index=True, description="SHA-256 hex of the link token")
    sealed_share: str = Field(nullable=False, description="Share sealed under the link key")
    created_at: datetime = Field(sa_type=DateTime, nullable=False)
    expires_at: datetime = Field(sa_type=DateTime, nullable=False, index=True)
