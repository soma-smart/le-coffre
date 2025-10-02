from typing import Protocol
from uuid import UUID


class UserManagementGateway(Protocol):
    async def create_admin(self, user_id: UUID, email: str, display_name: str) -> None:
        """Create an admin user in the user management context"""
        ...

    async def can_create_admin(self) -> bool:
        """Check if an admin can be created (no admin exists yet)"""
        ...

    async def create_user(self, user_id: UUID, email: str, display_name: str) -> None:
        """Create a regular user in the user management context"""
        ...
