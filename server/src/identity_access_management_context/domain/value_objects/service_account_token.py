import hashlib
import secrets
from dataclasses import dataclass, field
from functools import cached_property
from typing import ClassVar

from identity_access_management_context.domain.exceptions import InvalidServiceAccountTokenError


@dataclass(frozen=True)
class ServiceAccountToken:
    """The secret handed to a service account's operator.

    Domain Rules:
    - only ever built from generate(), or parsed back from an incoming request
    - shown once, at creation and at regeneration, and never again
    - never stored: persistence keeps hash so a database leak yields no
      usable credential
    """

    _n_token_bytes: ClassVar[int] = 32
    # 32 bytes of entropy, url-safe encoded. Same generator as the one-time link,
    # CSRF and SSO state tokens (see security/csrf_tokens.py). At this size the token
    # is not enumerable, which is what will let a future bearer-auth path trust a
    # lookup by hash alone.

    value: str = field(repr=False)
    """The value of the token."""

    @cached_property
    def _n_char_min(self) -> int:
        return len(secrets.token_urlsafe(self._n_token_bytes))

    def __post_init__(self) -> None:
        if len(self.value) < self._n_char_min:
            raise InvalidServiceAccountTokenError()

    @classmethod
    def generate(cls) -> "ServiceAccountToken":
        return cls(value=secrets.token_urlsafe(cls._n_token_bytes))

    @property
    def hash(self) -> str:
        """Hex SHA-256 of the token, the only form that reaches storage.

        A plain hash is enough here, unlike for user passwords: the input is 256
        bits of uniform randomness, so there is no dictionary to run against it
        and nothing for a work factor to slow down.

        This is also why the hash never reaches the audit log: it is directly
        verifiable against a candidate token, so a leaked event row would be as
        good as the credential to anyone already holding a guess.
        """
        return hashlib.sha256(self.value.encode()).hexdigest()
