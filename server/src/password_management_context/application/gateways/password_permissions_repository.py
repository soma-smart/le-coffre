from typing import Protocol
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission


class PasswordPermissionsRepository(Protocol):
    """Repository for managing password access permissions"""

    def set_owner(self, user_id: UUID, password_id: UUID) -> None:
        """Set a user as the owner of a password"""
        ...

    def is_owner(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if a user is the owner of a password"""
        ...

    def has_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> bool:
        """Check if a user has any access to a password (owner or shared)"""
        ...

    def grant_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
        """Grant a user access to a password with specific permission"""
        ...

    def revoke_access(self, user_id: UUID, password_id: UUID) -> None:
        """Revoke a user's access to a password"""
        ...

    def list_all_permissions_for(
        self, password_id: UUID
    ) -> dict[UUID, set[PasswordPermission]]:
        """Get all users who have access to a password with their permissions"""
        ...
