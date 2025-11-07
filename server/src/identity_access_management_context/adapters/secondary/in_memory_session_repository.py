from typing import Optional, Dict
from uuid import UUID

from identity_access_management_context.application.gateways import SessionRepository
from identity_access_management_context.domain.entities import AuthenticationSession


class InMemorySessionRepository(SessionRepository):
    def __init__(self):
        self._sessions: Dict[UUID, AuthenticationSession] = {}
        self._sessions_by_token: Dict[str, AuthenticationSession] = {}
        self._user_sessions: Dict[UUID, AuthenticationSession] = {}

    def save(self, session: AuthenticationSession) -> None:
        self._sessions[session.id] = session
        self._sessions_by_token[session.jwt_token] = session
        self._user_sessions[session.user_id] = session

    def get_by_id(self, session_id: UUID) -> Optional[AuthenticationSession]:
        return self._sessions.get(session_id)

    def get_by_token(self, jwt_token: str) -> Optional[AuthenticationSession]:
        return self._sessions_by_token.get(jwt_token)

    def get_user_last_session(self, user_id: UUID) -> Optional[AuthenticationSession]:
        return self._user_sessions.get(user_id)

    def delete(self, session_id: UUID) -> None:
        session = self._sessions.get(session_id)
        if session:
            del self._sessions[session_id]
            if session.jwt_token in self._sessions_by_token:
                del self._sessions_by_token[session.jwt_token]
            if (
                session.user_id in self._user_sessions
                and self._user_sessions[session.user_id].id == session_id
            ):
                del self._user_sessions[session.user_id]
