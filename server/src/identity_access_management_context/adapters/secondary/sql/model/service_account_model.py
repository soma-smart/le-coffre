from datetime import datetime
from uuid import UUID

from sqlmodel import DateTime, Field

from .principal_model import PrincipalDetailsTable, PrincipalKind


class ServiceAccountPrincipalTable(PrincipalDetailsTable, table=True):
    """A service account's details, keyed by its row in the principal registry."""

    __table_suffix__ = PrincipalKind.SERVICE_ACCOUNT.value

    group_id: UUID = Field(nullable=False, index=True)
    name: str = Field(nullable=False)
    revoked_at: datetime | None = Field(
        sa_type=DateTime, default=None, index=True, description="When the account was revoked"
    )
