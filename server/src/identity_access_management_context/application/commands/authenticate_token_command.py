from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class AuthenticateTokenCommand:
    token: str | None = field(repr=False)
    """The presented token, None when the caller presented none."""

    client_ip: str | None = None
    """Where the token came from, recorded when it is refused."""

    required_kind: Literal["user", "service_account"] | None = None
    """Refuse a token whose principal is of another kind. Any kind, if None."""
