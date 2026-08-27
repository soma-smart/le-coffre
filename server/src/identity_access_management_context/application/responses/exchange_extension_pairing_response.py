from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ExchangedExtensionTokenResponse:
    """Carries the only plaintext copy of the credential that will ever exist.

    Returned exactly once, by the exchange call. Only its SHA-256 is stored, so
    a caller that loses this response has to re-pair.
    """

    token: str
    token_id: UUID
    expires_at: datetime
    user_id: UUID
    email: str
    display_name: str


@dataclass
class PendingExtensionPairingResponse:
    """The pairing exists and the verifier matched, but nobody has approved yet."""

    expires_at: datetime
    poll_interval_seconds: int
