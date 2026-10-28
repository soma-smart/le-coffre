from datetime import datetime

from sqlmodel import DateTime, Field

from ._credential_record import CredentialKind, CredentialRecordDetailsTable


class TokenCredentialRecordTable(CredentialRecordDetailsTable, table=True):
    __table_suffix__ = CredentialKind.TOKEN.value

    token_hash: str = Field(nullable=False, unique=True, index=True, description="SHA-256 hex of the token")
    # Temporary, see TokenCredentialRecord.read_only.
    read_only: bool = Field(default=False, nullable=False)
    # Should not be here, see TokenCredentialRecord.label.
    label: str | None = Field(default=None, nullable=True)
    expires_at: datetime | None = Field(sa_type=DateTime, default=None, nullable=True)
    # Temporary, see TokenCredentialRecord.max_idle.
    last_used_at: datetime | None = Field(sa_type=DateTime, default=None, nullable=True)
    max_idle_seconds: int | None = Field(default=None, nullable=True)
