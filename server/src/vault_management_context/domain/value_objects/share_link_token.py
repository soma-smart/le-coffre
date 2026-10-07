import hashlib
import re
import secrets
from dataclasses import dataclass, field

from vault_management_context.domain.exceptions import InvalidShareLinkLookupError, ShareLinkAckRejectedError

# 32 bytes of entropy, url-safe encoded, like the one-time link tokens. At this
# size the token is not enumerable, which is what lets the retrieval endpoint
# stay anonymous.
TOKEN_BYTES = 32

# fullmatch, not match: with match, $ also accepts a trailing newline.
_HEX_256_PATTERN = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class ShareLinkToken:
    """The secret carried in the fragment of a share link URL.

    Three independent values are derived from it: the lookup hash, which
    addresses the link; the key that seals the share; and the acknowledgement
    key that closes the link (both in ShareSealingGateway). None can be
    computed from another.

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
class ShareLinkAckKey:
    """The proof a custodian sends to close their link once the share is saved.

    Derived in the browser from the token (see ShareSealingGateway.ack_hash),
    hex encoded. Malformed input is rejected like a wrong key: either way it
    did not come from the token.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not _HEX_256_PATTERN.fullmatch(self.value):
            raise ShareLinkAckRejectedError()

    def as_bytes(self) -> bytes:
        return bytes.fromhex(self.value)


@dataclass(frozen=True)
class ShareLinkLookupHash:
    """The address of a share link, as sent by the anonymous recipient.

    Domain Rules:
    - exactly 64 lowercase hex characters (a SHA-256 digest); anything else did
      not come from a real link and must not reach a database lookup
    """

    value: str

    def __post_init__(self) -> None:
        if not _HEX_256_PATTERN.fullmatch(self.value):
            raise InvalidShareLinkLookupError()
