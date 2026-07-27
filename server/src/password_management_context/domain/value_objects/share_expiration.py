from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from password_management_context.domain.exceptions import (
    ShareExpirationInPastError,
    ShareExpirationTooFarError,
)

# A temporary share is a convenience, not a security boundary the way a one-time
# link is: the recipient is an authenticated user who already went through login.
# The cap therefore exists to stop "temporary" from silently meaning "forever",
# not to keep the window short. A year covers the longest legitimate case we know
# of (a contractor's mission) and is overridable through configuration.
DEFAULT_MAX_SHARE_LIFETIME_SECONDS = 365 * 24 * 60 * 60


@dataclass(frozen=True)
class ShareExpiration:
    """The instant a shared access stops granting anything.

    Domain Rules:
    - strictly in the future, otherwise the share would be born dead
    - no further out than the configured maximum lifetime
    """

    value: datetime

    @classmethod
    def create(
        cls,
        expires_at: datetime,
        now: datetime,
        max_lifetime_seconds: int = DEFAULT_MAX_SHARE_LIFETIME_SECONDS,
    ) -> "ShareExpiration":
        normalised = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at.astimezone(UTC)

        if normalised <= now:
            raise ShareExpirationInPastError(normalised, now)

        furthest = now + timedelta(seconds=max_lifetime_seconds)
        if normalised > furthest:
            raise ShareExpirationTooFarError(normalised, max_lifetime_seconds)

        return cls(value=normalised)
