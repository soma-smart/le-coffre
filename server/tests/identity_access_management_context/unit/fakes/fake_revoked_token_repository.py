from datetime import datetime

from identity_access_management_context.application.gateways import ActiveRevocation, Token


class FakeRevokedTokenRepository:
    def __init__(self):
        self.revoked_tokens: dict[str, tuple[datetime | None, str]] = {}
        self.purge_calls = 0

    def revoke(self, token: Token, reason: str, revoked_at: datetime) -> None:
        if token.jti is None:
            return
        self.revoked_tokens[token.jti] = (token.expires_at, reason)

    def is_revoked(self, jti: str, now: datetime) -> bool:
        return self.get_active_revocation(jti, now) is not None

    def get_active_revocation(self, jti: str, now: datetime) -> ActiveRevocation | None:
        revoked = self.revoked_tokens.get(jti)
        if revoked is None:
            return None
        expires_at, reason = revoked
        if expires_at is not None and expires_at <= now:
            return None
        return ActiveRevocation(reason=reason)

    def purge_expired(self, now: datetime) -> None:
        self.purge_calls += 1
        expired_jtis = [
            jti for jti, (expires_at, _) in self.revoked_tokens.items() if expires_at is not None and expires_at <= now
        ]
        for jti in expired_jtis:
            del self.revoked_tokens[jti]

    def revoke_jti(self, jti: str, expires_at: datetime | None = None, reason: str = "test") -> None:
        self.revoked_tokens[jti] = (expires_at, reason)
