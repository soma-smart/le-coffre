from datetime import datetime
from uuid import UUID, uuid4

from identity_access_management_context.domain.entities import AuthSession


class FakeAuthSessionRepository:
    def __init__(self):
        self.sessions: dict[UUID, AuthSession] = {}
        self.purge_dead_cutoffs: list[datetime] = []

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

    def rotate_refresh_token_jti(
        self,
        session_id: UUID,
        expected_refresh_token_jti: str,
        new_refresh_token_jti: str,
        rotated_at: datetime,
    ) -> bool:
        session = self.sessions.get(session_id)
        if session is None or session.invalidated_at is not None:
            return False
        if session.current_refresh_token_jti != expected_refresh_token_jti:
            return False
        session.current_refresh_token_jti = new_refresh_token_jti
        session.updated_at = rotated_at
        return True

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

    def purge_dead(self, cutoff: datetime) -> None:
        self.purge_dead_cutoffs.append(cutoff)
        dead_session_ids = [
            session_id
            for session_id, session in self.sessions.items()
            if (session.invalidated_at is not None and session.invalidated_at < cutoff)
            or (session.invalidated_at is None and session.updated_at < cutoff)
        ]
        for session_id in dead_session_ids:
            del self.sessions[session_id]
