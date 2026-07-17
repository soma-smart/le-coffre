from datetime import datetime

from sqlmodel import Session, delete, select

from identity_access_management_context.adapters.secondary.sql.model.revoked_token_model import (
    RevokedTokenTable,
)
from identity_access_management_context.application.gateways import RevokedTokenRepository, Token
from shared_kernel.adapters.secondary.sql import SQLBaseRepository


class SqlRevokedTokenRepository(SQLBaseRepository, RevokedTokenRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def revoke(self, token: Token, reason: str, revoked_at: datetime) -> None:
        if token.jti is None:
            return

        self._purge_expired_tokens(revoked_at)

        existing = self._session.exec(select(RevokedTokenTable).where(RevokedTokenTable.jti == token.jti)).first()
        if existing is not None:
            return

        self._session.add(
            RevokedTokenTable(
                jti=token.jti,
                user_id=token.user_id,
                token_type=token.token_type,
                expires_at=token.expires_at,
                revoked_at=revoked_at,
                reason=reason,
            )
        )
        self.commit()

    def is_revoked(self, jti: str, now: datetime) -> bool:
        self._purge_expired_tokens(now)

        revoked_token = self._session.exec(select(RevokedTokenTable).where(RevokedTokenTable.jti == jti)).first()
        return revoked_token is not None

    def _purge_expired_tokens(self, now: datetime) -> None:
        self._session.exec(
            delete(RevokedTokenTable).where(
                RevokedTokenTable.expires_at.is_not(None),
                RevokedTokenTable.expires_at <= now,
            )
        )
        self.commit()
