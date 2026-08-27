from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class StartedExtensionPairingResponse:
    user_code: str
    expires_at: datetime
    poll_interval_seconds: int


@dataclass
class ExtensionPairingDetailsResponse:
    """What the approval page shows the user before they decide.

    Everything here except `device_name` is vouched for by the server.
    `device_name` is self-reported by the extension, so the page must label it
    as untrusted rather than present it as fact.
    """

    user_code: str
    device_name: str
    created_at: datetime
    expires_at: datetime
    created_from_ip: str | None
    is_resolved: bool


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


@dataclass
class ExtensionTokenSummary:
    id: UUID
    device_name: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_from_ip: str | None
    is_active: bool


@dataclass
class ListExtensionTokensResponse:
    tokens: list[ExtensionTokenSummary]


@dataclass
class ValidatedExtensionTokenResponse:
    """The identity behind a bearer credential.

    `roles` is deliberately absent. The caller assembles a principal with a
    fixed non-admin role instead of echoing the user's own: an admin's
    extension token would otherwise make `/passwords/list` return the names,
    logins and URLs of every secret on the instance, and that list would be
    sitting in a browser profile.
    """

    user_id: UUID
    email: str
    display_name: str
    token_id: UUID
