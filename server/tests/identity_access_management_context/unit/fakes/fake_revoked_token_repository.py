from datetime import datetime

from identity_access_management_context.application.gateways import Token


class FakeRevokedTokenRepository:
    def __init__(self):
        self.revoked_tokens: dict[str, tuple[datetime | None, str]] = {}

    def revoke(self, token: Token, reason: str, revoked_at: datetime) -> None:
        self.revoked_tokens[token.jti or token.value] = (token.expires_at, reason)

    def is_revoked(self, jti: str, now: datetime) -> bool:
        revoked = self.revoked_tokens.get(jti)
        if revoked is None:
            return False
        expires_at, _ = revoked
        if expires_at is not None and expires_at <= now:
            del self.revoked_tokens[jti]
            return False
        return True

    def revoke_jti(self, jti: str, expires_at: datetime | None = None, reason: str = "test") -> None:
        self.revoked_tokens[jti] = (expires_at, reason)
