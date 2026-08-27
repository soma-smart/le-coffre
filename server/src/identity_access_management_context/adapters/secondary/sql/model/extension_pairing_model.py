from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ExtensionPairingTable(SQLModel, table=True):
    """An in-flight request to connect one browser extension to one account.

    Rows are kept after approval, denial or redemption so the pairing stays
    auditable, which is why every outcome is a timestamp rather than a deletion.
    """

    __tablename__: str = "ExtensionPairing"

    id: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, index=True)
    # Shown in BOTH the extension popup and the approval page so the user can
    # match them. Not a secret: redeeming also requires the PKCE verifier.
    user_code: str = Field(nullable=False, unique=True, index=True)
    # base64url(SHA-256(verifier)). The verifier itself never reaches the server
    # until the exchange call, which is what binds redemption to the device that
    # started the pairing.
    code_challenge: str = Field(nullable=False)
    device_name: str = Field(nullable=False)
    created_at: datetime = Field(nullable=False)
    expires_at: datetime = Field(nullable=False, index=True)
    approved_at: datetime | None = Field(default=None, nullable=True)
    approved_by_user_id: UUID | None = Field(default=None, nullable=True, index=True)
    denied_at: datetime | None = Field(default=None, nullable=True)
    consumed_at: datetime | None = Field(default=None, nullable=True)
    # Shown on the approval page: a foreign address is what gives away a remote
    # attacker who started the pairing.
    created_from_ip: str | None = Field(default=None, nullable=True)
