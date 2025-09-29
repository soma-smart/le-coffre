from dataclasses import dataclass
from uuid import UUID
from typing import List


@dataclass
class AuthenticatedUser:
    user_id: UUID
    roles: List[str]


@dataclass
class ValidatedUser:
    user_id: UUID
    email: str
    display_name: str
    roles: List[str]
    session_id: UUID

    def to_authenticated_user(self) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=self.user_id,
            roles=self.roles,
        )
