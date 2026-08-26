import hashlib
import secrets
from dataclasses import dataclass, field

from identity_access_management_context.domain.exceptions import (
    InvalidExtensionTokenError,
)

# 32 bytes of entropy, url-safe encoded. Same generator as the one-time link,
# CSRF and SSO state tokens. At this size the token is not enumerable, which is
# what lets the exchange endpoint stay anonymous.
TOKEN_BYTES = 32

# token_urlsafe(32) yields 43 characters. Anything shorter did not come from
# generate() and must not be trusted enough to reach a database lookup.
MIN_TOKEN_LENGTH = 43


@dataclass(frozen=True)
class ExtensionTokenSecret:
    """The bearer credential a paired browser extension holds.

    Domain Rules:
    - only ever built from generate(), or parsed back from an incoming request
    - never stored: persistence keeps hashed(), so a database leak yields no
      usable credential

    Deliberately opaque rather than a JWT. Three reasons, in order of weight:
    revocation needs a row per device anyway (the "connected devices" screen),
    so statelessness buys nothing; roles must be resolved fresh on every request
    rather than frozen at mint, or a demoted admin keeps their role for the
    token's whole 30-day life; and a JWT signed with JWT_SECRET_KEY carrying
    user_id/email/roles is shaped *exactly* like a session access token, so one
    misrouted value would silently upgrade a read-only credential into a full
    session. A random string cannot validate against JwtTokenGateway at all.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if len(self.value) < MIN_TOKEN_LENGTH:
            raise InvalidExtensionTokenError()

    def __str__(self) -> str:
        return "ExtensionTokenSecret(***)"

    @classmethod
    def generate(cls) -> "ExtensionTokenSecret":
        return cls(value=secrets.token_urlsafe(TOKEN_BYTES))

    def hashed(self) -> str:
        """Hex SHA-256 of the token, the only form that reaches storage.

        A plain hash is enough here, unlike for user passwords: the input is 256
        bits of uniform randomness, so there is no dictionary to run against it
        and nothing for a work factor to slow down.
        """
        return hashlib.sha256(self.value.encode()).hexdigest()
