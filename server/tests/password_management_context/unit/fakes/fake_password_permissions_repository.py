from typing import Dict, Set, Tuple
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission


class FakePasswordPermissionsRepository:
    def __init__(self):
        self._ownerships: Dict[Tuple[UUID, UUID], bool] = {}
        self._permissions: Dict[Tuple[UUID, UUID], Set[PasswordPermission]] = {}

    def set_owner(self, owner_id: UUID, password_id: UUID) -> None:
        self._ownerships[(owner_id, password_id)] = True

    def is_owner(self, owner_id: UUID, password_id: UUID) -> bool:
        return self._ownerships.get((owner_id, password_id), False)

    def has_access(
        self, group_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> bool:
        # Check if group is the owner
        if self.is_owner(group_id, password_id):
            return True

        # Check if group has explicit permissions
        key = (group_id, password_id)
        return key in self._permissions and permission in self._permissions[key]

    def grant_access(
        self, group_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
        key = (group_id, password_id)
        if key not in self._permissions:
            self._permissions[key] = set()
        self._permissions[key].add(permission)

    def revoke_access(self, group_id: UUID, password_id: UUID) -> None:
        key = (group_id, password_id)
        if key in self._permissions:
            del self._permissions[key]

    def list_all_permissions_for(
        self, password_id: UUID
    ) -> dict[UUID, tuple[bool, set[PasswordPermission]]]:
        result: dict[UUID, tuple[bool, set[PasswordPermission]]] = {}

        # First, add owner groups (owners take precedence)
        for owner_id, pwd_id in self._ownerships:
            if pwd_id == password_id:
                result[owner_id] = (True, set())

        # Then add groups with explicit permissions (only if not already owners)
        for (group_id, pwd_id), permissions in self._permissions.items():
            if pwd_id == password_id and group_id not in result:
                result[group_id] = (False, permissions.copy())

        return result

    def clear(self) -> None:
        self._ownerships.clear()
        self._permissions.clear()
