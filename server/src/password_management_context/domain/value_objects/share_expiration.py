from dataclasses import dataclass
from datetime import UTC, datetime

from password_management_context.domain.exceptions import ShareExpirationInPastError


@dataclass(frozen=True)
class ShareExpiration:
    """The instant a shared access stops granting anything.

    Domain Rule: strictly in the future, otherwise the share would be born dead.

    There is deliberately no upper bound. Sharing permanently is already
    available and unbounded, so a cap would forbid nothing: it would only push
    someone who needs a three-year access to pick "permanent" instead, trading a
    long but self-closing share for one that never closes at all.
    """

    value: datetime

    @classmethod
    def create(cls, expires_at: datetime, now: datetime) -> "ShareExpiration":
        normalised = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at.astimezone(UTC)

        if normalised <= now:
            raise ShareExpirationInPastError(normalised, now)

        return cls(value=normalised)
