from dataclasses import dataclass
from datetime import datetime, timedelta

from shared_kernel.domain.entities.credential_record import CredentialRecord


@dataclass(kw_only=True)
class TokenCredentialRecord(CredentialRecord):
    """The hash of the token a principal presents.

    Only the hash is kept: the token itself is shown once, when issued.
    """

    token_hash: str

    read_only: bool = False
    """Whether the token only reads what its principal can access: no writes, no admin privileges.

    Temporary: stands in for a proper permission and grant system, which should
    decide what a credential may do instead of a flag on it.
    """

    label: str | None = None
    """What the holder calls this token, e.g. the device it lives on.

    Should not be here: it describes the token to humans, it plays no part in
    authenticating it.
    """

    expires_at: datetime | None = None
    """When the token stops working, whether used or not. Never, if None."""

    last_used_at: datetime | None = None
    """When the token was last presented, coarsened. Set at issuance.

    Temporary: only kept to enforce `max_idle`.
    """

    max_idle: timedelta | None = None
    """How long the token may go unused before it stops working. Forever, if None.

    Temporary: an inactivity rule carried by the credential until a grant
    system owns such policies.
    """

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at

    def is_idle(self, now: datetime) -> bool:
        if self.max_idle is None or self.last_used_at is None:
            return False
        return now - self.last_used_at >= self.max_idle

    def is_usable(self, now: datetime) -> bool:
        """Whether presenting this token still proves its principal."""
        return not self.is_expired(now) and not self.is_idle(now)
