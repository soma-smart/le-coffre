from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from identity_access_management_context.application.gateways.token_gateway import Token

REVOCATION_REASON_LOGOUT = "logout"  # noqa: S105
REVOCATION_REASON_REFRESH_TOKEN_ROTATED = "refresh_token_rotated"  # noqa: S105


@dataclass(frozen=True)
class ActiveRevocation:
    reason: str


class RevokedTokenRepository(Protocol):
    def revoke(self, token: Token, reason: str, revoked_at: datetime) -> None: ...

    def is_revoked(self, jti: str, now: datetime) -> bool: ...

    def get_active_revocation(self, jti: str, now: datetime) -> ActiveRevocation | None: ...

    def purge_expired(self, now: datetime) -> None: ...
