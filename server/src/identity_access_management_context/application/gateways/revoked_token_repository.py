from datetime import datetime
from typing import Protocol

from identity_access_management_context.application.gateways.token_gateway import Token


class RevokedTokenRepository(Protocol):
    def revoke(self, token: Token, reason: str, revoked_at: datetime) -> None: ...

    def is_revoked(self, jti: str, now: datetime) -> bool: ...
