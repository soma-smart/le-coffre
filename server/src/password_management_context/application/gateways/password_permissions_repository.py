from typing import Protocol
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission

GroupPermissions = dict[UUID, tuple[bool, set[PasswordPermission]]]
BulkGroupPermissions = dict[UUID, GroupPermissions]


class PasswordPermissionsRepository(Protocol):
    """Repository for managing password access permissions"""

    def set_owner(self, owner_id: UUID, password_id: UUID) -> None:
        """Set an owner (user or group) of a password"""
        ...

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        """Check if an owner (user or group) is the owner of a password"""
        ...

    def has_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> bool:
        """Check if a user has any access to a password (owner or shared)"""
        ...

    def grant_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> None:
        """Grant a user access to a password with specific permission"""
        ...

    def revoke_access(self, group_id: UUID, password_id: UUID) -> None:
        """Revoke a group's access to a password"""
        ...

    def list_all_permissions_for(self, password_id: UUID) -> GroupPermissions:
        """Get all groups who have access to a password with their permissions"""
        ...

    def list_all_permissions_for_bulk(self, password_ids: list[UUID]) -> BulkGroupPermissions:
        """Get all group permissions for multiple passwords in a single call.

        Returns {password_id -> {group_id -> (is_owner, permissions)}}
        """
        ...

    def has_any_password_for_group(self, group_id: UUID) -> bool:
        """Check if a group has any password (as owner or with access)"""
        ...

    def revoke_all_access_for_password(self, password_id: UUID):
        """Revoke all access (permissions and ownerships) for a specific password"""
        ...

    def revoke_all_access_for_owner_group(self, group_id: UUID) -> None:
        """Revoke all access (permissions and ownerships) for all passwords owned by a group"""
        ...
