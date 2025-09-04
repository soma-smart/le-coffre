from typing import Dict, List, Optional
from uuid import UUID

from authentication_context.domain.entities import AuthenticationSession


class FakeSessionRepository:
    def __init__(self):
        self._sessions: Dict[UUID, AuthenticationSession] = {}

    def save(self, session: AuthenticationSession) -> None:
        self._sessions[session.id] = session

    def get_by_id(self, session_id: UUID) -> Optional[AuthenticationSession]:
        return self._sessions.get(session_id)

    def get_by_token(self, jwt_token: str) -> Optional[AuthenticationSession]:
        for session in self._sessions.values():
            if session.jwt_token == jwt_token:
                return session
        return None

    def get_sessions_by_user_id_ordered_by_creation(
        self, user_id: UUID
    ) -> List[AuthenticationSession]:
        return sorted(
            [
                session
                for session in self._sessions.values()
                if session.user_id == user_id
            ],
            key=lambda session: session.created_at,
        )

    def delete(self, session_id: UUID) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
