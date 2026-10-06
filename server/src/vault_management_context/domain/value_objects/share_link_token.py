import hashlib
import re
import secrets
from dataclasses import dataclass, field

from vault_management_context.domain.exceptions import InvalidShareLinkLookupError

# 32 bytes of entropy, url-safe encoded, like the one-time link tokens. At this
# size the token is not enumerable, which is what lets the retrieval endpoint
# stay anonymous.
TOKEN_BYTES = 32

_LOOKUP_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ShareLinkToken:
    """The secret carried in the fragment of a share link URL.

    Two independent values are derived from it: the lookup hash, which is all
    the server ever stores or receives, and the key that seals the share (see
    ShareSealingGateway). Neither can be computed from the other.

    Domain Rules:
    - only ever built from generate(); it exists server side for the duration
      of the setup request and is never persisted
    """

    value: str = field(repr=False)

    def __str__(self) -> str:
        return "ShareLinkToken(***)"

    @classmethod
    def generate(cls) -> "ShareLinkToken":
        return cls(value=secrets.token_urlsafe(TOKEN_BYTES))

    def lookup_hash(self) -> str:
        """Hex SHA-256 of the token, the only form that reaches storage.

        The browser computes the same value from the fragment to address the
        link, so the token itself never travels back to the server.
        """
        return hashlib.sha256(self.value.encode()).hexdigest()


@dataclass(frozen=True)
class ShareLinkLookupHash:
    """The address of a share link, as sent by the anonymous recipient.

    Domain Rules:
    - exactly 64 lowercase hex characters (a SHA-256 digest); anything else did
      not come from a real link and must not reach a database lookup
    """

    value: str

    def __post_init__(self) -> None:
        if not _LOOKUP_HASH_PATTERN.match(self.value):
            raise InvalidShareLinkLookupError()
