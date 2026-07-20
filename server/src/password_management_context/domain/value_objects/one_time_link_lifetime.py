from dataclasses import dataclass
from datetime import timedelta

from password_management_context.domain.exceptions import (
    OneTimeLinkLifetimeTooLongError,
    OneTimeLinkLifetimeTooShortError,
)

# A one-time link hands a decrypted secret to whoever holds the URL, with no
# authentication in front of it. Its lifetime is therefore mandatory and short:
# the window during which a leaked URL is exploitable is the whole attack surface.
DEFAULT_LIFETIME_SECONDS = 24 * 60 * 60

# Below five minutes the link is unusable in practice: the recipient has to
# receive the message, open it and click through before it dies.
MIN_LIFETIME_SECONDS = 5 * 60

# Seven days is the point past which "short-lived" stops being true. Anything
# longer should be a real share with a group, not a one-time link.
MAX_LIFETIME_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class OneTimeLinkLifetime:
    """How long a one-time link stays consumable, in seconds.

    Domain Rules:
    - at least MIN_LIFETIME_SECONDS, so the link survives long enough to be used
    - at most MAX_LIFETIME_SECONDS, so it stays a short-lived secret
    """

    seconds: int

    def __post_init__(self) -> None:
        if self.seconds < MIN_LIFETIME_SECONDS:
            raise OneTimeLinkLifetimeTooShortError(self.seconds, MIN_LIFETIME_SECONDS)
        if self.seconds > MAX_LIFETIME_SECONDS:
            raise OneTimeLinkLifetimeTooLongError(self.seconds, MAX_LIFETIME_SECONDS)

    @classmethod
    def default(cls) -> "OneTimeLinkLifetime":
        return cls(seconds=DEFAULT_LIFETIME_SECONDS)

    def as_timedelta(self) -> timedelta:
        return timedelta(seconds=self.seconds)
