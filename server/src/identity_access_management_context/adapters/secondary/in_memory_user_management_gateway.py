from uuid import UUID
from dataclasses import dataclass

from identity_access_management_context.application.gateways import UserManagementGateway


@dataclass
class User:
    user_id: UUID
    email: str
    display_name: str


class InMemoryUserManagementGateway(UserManagementGateway):
    def __init__(self):
        self._admin_exists = False
        self._created_admins: list[User] = []
        self._created_users: list[User] = []

    async def create_admin(self, user_id: UUID, email: str, display_name: str) -> None:
        self._admin_exists = True
        self._created_admins.append(
            User(
                user_id=user_id,
                email=email,
                display_name=display_name,
            )
        )

    async def can_create_admin(self) -> bool:
        return not self._admin_exists

    async def create_user(self, user_id: UUID, email: str, display_name: str) -> None:
        """Create a regular user in the user management context"""
        self._created_users.append(
            User(
                user_id=user_id,
                email=email,
                display_name=display_name,
            )
        )
