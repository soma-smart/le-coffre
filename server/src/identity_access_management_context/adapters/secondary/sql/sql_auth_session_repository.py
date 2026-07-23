from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from identity_access_management_context.adapters.secondary.sql.model.auth_session_model import AuthSessionTable
from identity_access_management_context.application.gateways import AuthSessionRepository
from identity_access_management_context.domain.entities import AuthSession
from shared_kernel.adapters.secondary.sql import SQLBaseRepository


class SqlAuthSessionRepository(SQLBaseRepository, AuthSessionRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def create_session(self, user_id: UUID, refresh_token_jti: str, created_at: datetime) -> AuthSession:
        db_obj = AuthSessionTable(
            user_id=user_id,
            current_refresh_token_jti=refresh_token_jti,
            created_at=created_at,
            updated_at=created_at,
            invalidated_at=None,
        )
        self._session.add(db_obj)
        self.commit_and_refresh(db_obj)
        return self._to_entity(db_obj)

    def get_active_by_user_id_and_refresh_jti(self, user_id: UUID, refresh_token_jti: str) -> AuthSession | None:
        statement = select(AuthSessionTable).where(
            AuthSessionTable.user_id == user_id,
            AuthSessionTable.current_refresh_token_jti == refresh_token_jti,
            AuthSessionTable.invalidated_at.is_(None),
        )
        row = self._session.exec(statement).first()
        return self._to_entity(row) if row is not None else None

    def rotate_refresh_token_jti(self, session_id: UUID, new_refresh_token_jti: str, rotated_at: datetime) -> None:
        statement = select(AuthSessionTable).where(
            AuthSessionTable.id == session_id,
            AuthSessionTable.invalidated_at.is_(None),
        )
        row = self._session.exec(statement).first()
        if row is None:
            return

        row.current_refresh_token_jti = new_refresh_token_jti
        row.updated_at = rotated_at
        self._session.add(row)
        self.commit_and_refresh(row)

    def invalidate_by_user_id_and_refresh_jti(
        self, user_id: UUID, refresh_token_jti: str, invalidated_at: datetime
    ) -> None:
        statement = select(AuthSessionTable).where(
            AuthSessionTable.user_id == user_id,
            AuthSessionTable.current_refresh_token_jti == refresh_token_jti,
            AuthSessionTable.invalidated_at.is_(None),
        )
        row = self._session.exec(statement).first()
        if row is None:
            return

        row.invalidated_at = invalidated_at
        row.updated_at = invalidated_at
        self._session.add(row)
        self.commit_and_refresh(row)

    def invalidate_all_for_user(self, user_id: UUID, invalidated_at: datetime) -> None:
        statement = select(AuthSessionTable).where(
            AuthSessionTable.user_id == user_id,
            AuthSessionTable.invalidated_at.is_(None),
        )
        rows = self._session.exec(statement).all()
        for row in rows:
            row.invalidated_at = invalidated_at
            row.updated_at = invalidated_at
            self._session.add(row)
        self.commit()

    def _to_entity(self, table: AuthSessionTable) -> AuthSession:
        return AuthSession(
            id=table.id,
            user_id=table.user_id,
            current_refresh_token_jti=table.current_refresh_token_jti,
            created_at=table.created_at,
            updated_at=table.updated_at,
            invalidated_at=table.invalidated_at,
        )
