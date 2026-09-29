import base64
import hashlib
import re
import secrets
from dataclasses import dataclass, field

from identity_access_management_context.domain.exceptions import (
    InvalidPkceVerifierError,
    UnsupportedPkceMethodError,
)

VERIFIER_BYTES = 32

# RFC 7636 section 4.1: 43 to 128 characters from the unreserved set. The floor
# is the entropy bound; the ceiling and the alphabet exist so that the anonymous
# registration and exchange endpoints hash and compare bounded, well-formed
# input rather than whatever a caller chose to send.
MIN_VERIFIER_LENGTH = 43
MAX_VERIFIER_LENGTH = 128
_VERIFIER_SHAPE = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")

# base64url(SHA-256(...)) without padding is always exactly 43 characters.
_CHALLENGE_SHAPE = re.compile(r"^[A-Za-z0-9_-]{43}$")

# The only method this system accepts. `plain` is rejected explicitly rather
# than left to a default, so a client cannot negotiate the protection away.
S256 = "S256"


def _b64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


@dataclass(frozen=True)
class PkceVerifier:
    """The secret the extension keeps for itself during pairing.

    It never leaves the extension until the exchange call, which is what binds
    the exchange to the device that started the pairing: someone who watches the
    user_code over the user's shoulder, or reads it out of the URL fragment,
    still cannot redeem the pairing.
    """

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not _VERIFIER_SHAPE.fullmatch(self.value):
            raise InvalidPkceVerifierError()

    def __str__(self) -> str:
        return "PkceVerifier(***)"

    @classmethod
    def generate(cls) -> "PkceVerifier":
        return cls(value=secrets.token_urlsafe(VERIFIER_BYTES))

    def challenge(self) -> "PkceChallenge":
        return PkceChallenge(value=_b64url_sha256(self.value))


@dataclass(frozen=True)
class PkceChallenge:
    """base64url(SHA-256(verifier)), the public half, safe to persist."""

    value: str

    def __post_init__(self) -> None:
        # A value of any other shape cannot be a SHA-256 digest, so it could
        # never match a verifier; refusing it at registration says so up front
        # instead of storing a pairing that no exchange can ever redeem.
        if not _CHALLENGE_SHAPE.fullmatch(self.value):
            raise InvalidPkceVerifierError()

    @classmethod
    def parse(cls, value: str, method: str) -> "PkceChallenge":
        """Build from an incoming request, refusing anything but S256."""
        if method != S256:
            raise UnsupportedPkceMethodError(method)
        return cls(value=value)

    def matches(self, verifier: PkceVerifier) -> bool:
        # Constant-time: the challenge is public but the comparison result gates
        # credential issuance, and a timing oracle on it would let an attacker
        # discover a valid verifier byte by byte.
        return secrets.compare_digest(self.value, _b64url_sha256(verifier.value))
