from datetime import datetime
from typing import Any, cast

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

        existing = self._session.exec(select(RevokedTokenTable).where(RevokedTokenTable.jti == token.jti)).first()
        if existing is None:
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
        expires_at_column = cast(Any, RevokedTokenTable.expires_at)
        revoked_token = self._session.exec(
            select(RevokedTokenTable).where(
                RevokedTokenTable.jti == jti,
                (expires_at_column.is_(None)) | (expires_at_column > now),
            )
        ).first()
        return revoked_token is not None

    def purge_expired(self, now: datetime) -> None:
        expires_at_column = cast(Any, RevokedTokenTable.expires_at)
        self._session.exec(
            delete(RevokedTokenTable).where(
                expires_at_column.is_not(None),
                expires_at_column <= now,
            )
        )
        self.commit()
