import hashlib
import secrets
from dataclasses import dataclass, field

from password_management_context.domain.exceptions import InvalidOneTimeLinkTokenError

# 32 bytes of entropy, url-safe encoded. Same generator as the CSRF and SSO state
# tokens (see security/csrf_tokens.py). At this size the token is not enumerable,
# which is what lets the consume endpoint stay anonymous.
TOKEN_BYTES = 32

# token_urlsafe(32) yields 43 characters. Anything shorter did not come from
# generate() and must not be trusted enough to reach a database lookup.
MIN_TOKEN_LENGTH = 43


@dataclass(frozen=True)
class OneTimeLinkToken:
    """The secret carried by a one-time link URL.

    Domain Rules:
    - only ever built from generate(), or parsed back from an incoming request
    - never stored: persistence keeps hashed() so a database leak yields no
      usable link
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.value) < MIN_TOKEN_LENGTH:
            raise InvalidOneTimeLinkTokenError()

    def __str__(self) -> str:
        return "OneTimeLinkToken(***)"

    @classmethod
    def generate(cls) -> "OneTimeLinkToken":
        return cls(value=secrets.token_urlsafe(TOKEN_BYTES))

    def hashed(self) -> str:
        """Hex SHA-256 of the token, the only form that reaches storage.

        A plain hash is enough here, unlike for user passwords: the input is 256
        bits of uniform randomness, so there is no dictionary to run against it
        and nothing for a work factor to slow down.
        """
        return hashlib.sha256(self.value.encode()).hexdigest()
