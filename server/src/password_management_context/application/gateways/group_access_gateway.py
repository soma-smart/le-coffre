from typing import Protocol
from uuid import UUID


class GroupAccessGateway(Protocol):
    """Gateway to verify group access for password management operations"""

    def is_principal_owner_of_group(self, principal_id: UUID, group_id: UUID) -> bool:
        """Verify if a principal owns a specific group"""
        ...

    def is_principal_member_of_group(self, principal_id: UUID, group_id: UUID) -> bool:
        """Verify if a principal is a member of a specific group"""
        ...

    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists in the system"""
        ...

    def get_group_owner_principals(self, group_id: UUID) -> list[UUID]:
        """Get all principals who own this group"""
        ...

    def get_group_member_principals(self, group_id: UUID) -> list[UUID]:
        """Get the principals who belong to this group as members (not owners)"""
        ...

    def group_owns_passwords(self, group_id: UUID) -> bool:
        """Check if a group owns any passwords"""
        ...
