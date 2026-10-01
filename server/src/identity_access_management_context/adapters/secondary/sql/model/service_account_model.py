from datetime import datetime
from uuid import UUID

from sqlmodel import Field

from .principal_model import PrincipalDetailsTable


class ServiceAccountPrincipalTable(PrincipalDetailsTable, table=True):
    """A service account's details, keyed by its row in the principal registry."""

    __table_suffix__ = "service_account"

    group_id: UUID = Field(nullable=False, index=True)
    name: str = Field(nullable=False)
    token_hash: str = Field(
        nullable=False, unique=True, index=True, description="SHA-256 hex of the service account token"
    )
    revoked_at: datetime | None = Field(default=None, index=True, description="When the account was revoked")
