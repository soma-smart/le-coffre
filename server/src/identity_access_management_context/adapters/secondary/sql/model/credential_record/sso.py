from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint
from sqlmodel import DateTime, Field

from ._credential_record import CredentialKind, CredentialRecordDetailsTable


class SSOCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.SSO.value
    __table_args__ = (UniqueConstraint("provider", "subject"),)

    provider: str = Field(nullable=False, description="SSO provider name")
    subject: str = Field(nullable=False, description="Subject identifier given by the provider")
    created_at: datetime | None = Field(
        sa_type=DateTime,
        description="Creation timestamp",
        nullable=True,
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_login: datetime | None = Field(
        sa_type=DateTime,
        description="Last login timestamp",
        nullable=True,
        default_factory=lambda: datetime.now(timezone.utc),
    )
