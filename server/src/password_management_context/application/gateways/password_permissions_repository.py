from datetime import datetime
from typing import Protocol
from uuid import UUID

from password_management_context.domain.value_objects import (
    PasswordGroupAccess,
    PasswordPermission,
)

GroupPermissions = dict[UUID, PasswordGroupAccess]
BulkGroupPermissions = dict[UUID, GroupPermissions]


class PasswordPermissionsRepository(Protocol):
    """Repository for managing password access permissions"""

    def set_owner(self, owner_id: UUID, password_id: UUID) -> None:
        """Set an owner (user or group) of a password"""
        ...

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        """Check if an owner (user or group) is the owner of a password"""
        ...

    def has_access_ignoring_expiry(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> bool:
        """Check whether a group was ever granted this permission, deadline aside.

        Answers "is this group listed on this password", not "may it read the
        password right now": a lapsed share still counts here. Deciding access
        is PasswordGroupAccess.grants_read(now)'s job, reached through
        list_all_permissions_for. The name is deliberately awkward so that
        reaching for it as an authorization check reads as a mistake.
        """
        ...

    def grant_access(
        self,
        group_id: UUID,
        password_id: UUID,
        permission: PasswordPermission,
        expires_at: datetime | None = None,
    ) -> None:
        """Grant a group access to a password, permanently or until expires_at.

        Re-granting an existing permission overwrites its expiry, so re-sharing
        with a different duration is an update rather than a silent no-op.
        """
        ...

    def update_access_expiration(self, group_id: UUID, password_id: UUID, expires_at: datetime | None) -> bool:
        """Change when an existing share expires; None makes it permanent.

        Returns False when the group holds no share for this password.
        """
        ...

    def revoke_access(self, group_id: UUID, password_id: UUID) -> None:
        """Revoke a group's access to a password"""
        ...

    def purge_expired_shares(self, cutoff: datetime) -> int:
        """Delete shares that expired before cutoff, returning how many were removed.

        Expiry is enforced when access is read, so this is hygiene only: it keeps
        long-dead rows from accumulating, while leaving recently expired ones in
        place so their owner can still see and extend them.
        """
        ...

    def list_all_permissions_for(self, password_id: UUID) -> GroupPermissions:
        """Get all groups who have access to a password with their permissions.

        Expired shares are included: this is the raw state, and it is each
        caller's job to decide whether an expired access counts. Deciders should
        go through PasswordGroupAccess.grants_read(now).
        """
        ...

    def list_all_permissions_for_bulk(self, password_ids: list[UUID]) -> BulkGroupPermissions:
        """Get all group permissions for multiple passwords in a single call.

        Returns {password_id -> {group_id -> PasswordGroupAccess}}
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
