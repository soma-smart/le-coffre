from typing import Protocol, List, Optional
from uuid import UUID

from identity_access_management_context.domain.entities import AuthenticationSession


class SessionRepository(Protocol):
    def save(self, session: AuthenticationSession) -> None:
        """Save an authentication session"""
        ...

    def get_by_id(self, session_id: UUID) -> Optional[AuthenticationSession]:
        """Get a session by ID"""
        ...

    def get_by_token(self, jwt_token: str) -> Optional[AuthenticationSession]:
        """Get a session by JWT token"""
        ...

    def get_user_last_session(self, user_id: UUID) -> Optional[AuthenticationSession]:
        """Get the last session for a user"""
        ...

    def delete(self, session_id: UUID) -> None:
        """Delete a session"""
        ...
