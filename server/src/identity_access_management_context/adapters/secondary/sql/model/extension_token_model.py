from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ExtensionTokenTable(SQLModel, table=True):
    """A long-lived, read-only bearer credential held by one paired extension.

    Deliberately a different table from ExtensionPairing: a pending or denied
    pairing must never occupy a row here, so "a row exists in ExtensionToken"
    always means "a credential was actually issued".
    """

    __tablename__: str = "ExtensionToken"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    user_id: UUID = Field(nullable=False, index=True)
    # SHA-256 hex of the bearer value. The plaintext exists only in the exchange
    # response body and in the extension's own storage, never here.
    token_hash: str = Field(nullable=False, unique=True, index=True)
    # Self-reported by the extension at pairing time, so it is untrusted input
    # and the approval page must label it as such.
    device_name: str = Field(nullable=False)
    created_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    last_used_at: datetime | None = Field(default=None, nullable=True)
    # A timestamp rather than a deletion, so a revoked pairing stays auditable.
    revoked_at: datetime | None = Field(default=None, nullable=True, index=True)
    created_from_ip: str | None = Field(default=None, nullable=True)
