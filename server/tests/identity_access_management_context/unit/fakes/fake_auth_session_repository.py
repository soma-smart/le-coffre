from datetime import datetime
from uuid import UUID, uuid4

from identity_access_management_context.domain.entities import AuthSession


class FakeAuthSessionRepository:
    def __init__(self):
        self.sessions: dict[UUID, AuthSession] = {}

    def create_session(self, user_id: UUID, refresh_token_jti: str, created_at: datetime) -> AuthSession:
        session = AuthSession(
            id=uuid4(),
            user_id=user_id,
            current_refresh_token_jti=refresh_token_jti,
            created_at=created_at,
            updated_at=created_at,
            invalidated_at=None,
        )
        self.sessions[session.id] = session
        return session

    def get_active_by_user_id_and_refresh_jti(self, user_id: UUID, refresh_token_jti: str) -> AuthSession | None:
        for session in self.sessions.values():
            if (
                session.user_id == user_id
                and session.current_refresh_token_jti == refresh_token_jti
                and session.invalidated_at is None
            ):
                return session
        return None

    def rotate_refresh_token_jti(self, session_id: UUID, new_refresh_token_jti: str, rotated_at: datetime) -> None:
        session = self.sessions.get(session_id)
        if session is None or session.invalidated_at is not None:
            return
        session.current_refresh_token_jti = new_refresh_token_jti
        session.updated_at = rotated_at

    def invalidate_by_user_id_and_refresh_jti(
        self, user_id: UUID, refresh_token_jti: str, invalidated_at: datetime
    ) -> None:
        session = self.get_active_by_user_id_and_refresh_jti(user_id, refresh_token_jti)
        if session is None:
            return
        session.invalidated_at = invalidated_at
        session.updated_at = invalidated_at

    def invalidate_all_for_user(self, user_id: UUID, invalidated_at: datetime) -> None:
        for session in self.sessions.values():
            if session.user_id == user_id and session.invalidated_at is None:
                session.invalidated_at = invalidated_at
                session.updated_at = invalidated_at
