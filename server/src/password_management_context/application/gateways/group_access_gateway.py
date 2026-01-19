from typing import Protocol
from uuid import UUID


class GroupAccessGateway(Protocol):
    """Gateway to verify group access for password management operations"""

    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        """Verify if a user owns a specific group"""
        ...

    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists in the system"""
        ...

    def get_group_owner_users(self, group_id: UUID) -> list[UUID]:
        """Get all users who own this group"""
        ...
