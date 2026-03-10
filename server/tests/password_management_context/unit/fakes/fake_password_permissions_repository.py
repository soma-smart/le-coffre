from typing import Dict, Set, Tuple
from uuid import UUID

from password_management_context.application.gateways.password_permissions_repository import (
    BulkGroupPermissions,
    GroupPermissions,
)
from password_management_context.domain.value_objects import PasswordPermission


class FakePasswordPermissionsRepository:
    def __init__(self):
        self._ownerships: Dict[Tuple[UUID, UUID], bool] = {}
        self._permissions: Dict[Tuple[UUID, UUID], Set[PasswordPermission]] = {}

    def set_owner(self, owner_id: UUID, password_id: UUID) -> None:
        self._ownerships[(owner_id, password_id)] = True

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        return self._ownerships.get((owner_id, password_id), False)

    def has_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> bool:
        # Check if group is the owner
        if self.is_owner(group_id, password_id):
            return True

        # Check if group has explicit permissions
        key = (group_id, password_id)
        return key in self._permissions and permission in self._permissions[key]

    def grant_access(self, group_id: UUID, password_id: UUID, permission: PasswordPermission) -> None:
        key = (group_id, password_id)
        if key not in self._permissions:
            self._permissions[key] = set()
        self._permissions[key].add(permission)

    def revoke_access(self, group_id: UUID, password_id: UUID) -> None:
        key = (group_id, password_id)
        if key in self._permissions:
            del self._permissions[key]

    def list_all_permissions_for(self, password_id: UUID) -> GroupPermissions:
        result: GroupPermissions = {}

        # First, add owner groups (owners take precedence)
        for owner_id, pwd_id in self._ownerships:
            if pwd_id == password_id:
                result[owner_id] = (True, set())

        # Then add groups with explicit permissions (only if not already owners)
        for (group_id, pwd_id), permissions in self._permissions.items():
            if pwd_id == password_id and group_id not in result:
                result[group_id] = (False, permissions.copy())

        return result

    def list_all_permissions_for_bulk(self, password_ids: list[UUID]) -> BulkGroupPermissions:
        return {pwd_id: self.list_all_permissions_for(pwd_id) for pwd_id in password_ids}

    def clear(self) -> None:
        self._ownerships.clear()
        self._permissions.clear()

    def has_any_password_for_group(self, group_id: UUID) -> bool:
        """Check if a group has any password (as owner or with access)"""
        # Check if group owns any password
        for owner_id, _ in self._ownerships:
            if owner_id == group_id:
                return True

        # Check if group has any permissions
        for grp_id, _ in self._permissions:
            if grp_id == group_id:
                return True

        return False

    def revoke_all_access_for_password(self, password_id: UUID):
        """Revoke all access (permissions and ownerships) for a specific password"""
        # Revoke all permissions for the password
        for grp_id, pwd_id in list(self._permissions.keys()):
            if pwd_id == password_id:
                del self._permissions[(grp_id, pwd_id)]

        for grp_id, pwd_id in list(self._ownerships.keys()):
            if pwd_id == password_id:
                del self._ownerships[(grp_id, pwd_id)]

    def revoke_all_access_for_owner_group(self, group_id: UUID) -> None:
        """Revoke all access (permissions and ownerships) for all passwords owned by a group"""
        # Find all passwords owned by this group
        password_ids_owned = [pwd_id for owner_id, pwd_id in self._ownerships.keys() if owner_id == group_id]

        # Revoke all access for each password owned by this group
        for password_id in password_ids_owned:
            self.revoke_all_access_for_password(password_id)
