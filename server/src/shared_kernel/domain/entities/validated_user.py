from dataclasses import dataclass
from uuid import UUID

from .authenticated_user import AuthenticatedUser


@dataclass
class ValidatedUser:
    user_id: UUID
    email: str
    display_name: str
    roles: list[str]

    def to_authenticated_user(self) -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=self.user_id,
            roles=self.roles,
        )
