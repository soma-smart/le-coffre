from typing import Dict, Optional
from uuid import UUID

from identity_access_management_context.domain.entities import AuthenticationSession


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

    def get_user_last_session(self, user_id: UUID) -> Optional[AuthenticationSession]:
        session_to_return = None
        for session in self._sessions.values():
            if not session.user_id == user_id:
                continue
            if not session_to_return:
                session_to_return = session
                continue
            if session.created_at > session_to_return.created_at:
                session_to_return = session

        return session_to_return

    def delete(self, session_id: UUID) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]
