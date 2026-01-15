from typing import Dict, Set, Tuple
from uuid import UUID

from password_management_context.domain.value_objects import PasswordPermission


class FakePasswordPermissionsRepository:
    def __init__(self):
        self._ownerships: Dict[Tuple[UUID, UUID], bool] = {}
        self._permissions: Dict[Tuple[UUID, UUID], Set[PasswordPermission]] = {}

    def set_owner(self, user_id: UUID, password_id: UUID) -> None:
        self._ownerships[(user_id, password_id)] = True

    def is_owner(self, user_id: UUID, password_id: UUID) -> bool:
        return self._ownerships.get((user_id, password_id), False)

    def has_access(self, user_id: UUID, password_id: UUID) -> bool:
        # Owner always has access
        if self.is_owner(user_id, password_id):
            return True
        # Check if user has explicit permissions
        return (user_id, password_id) in self._permissions

    def grant_access(
        self, user_id: UUID, password_id: UUID, permission: PasswordPermission
    ) -> None:
        key = (user_id, password_id)
        if key not in self._permissions:
            self._permissions[key] = set()
        self._permissions[key].add(permission)

    def revoke_access(self, user_id: UUID, password_id: UUID) -> None:
        key = (user_id, password_id)
        if key in self._permissions:
            del self._permissions[key]

    def get_all_users_with_access(
        self, password_id: UUID
    ) -> dict[UUID, set[PasswordPermission]]:
        result: dict[UUID, set[PasswordPermission]] = {}

        # Add users with explicit permissions
        for (user_id, pwd_id), permissions in self._permissions.items():
            if pwd_id == password_id:
                result[user_id] = permissions.copy()

        # Add owners (with empty permission set to distinguish them)
        for user_id, pwd_id in self._ownerships:
            if pwd_id == password_id:
                if user_id not in result:
                    result[user_id] = set()

        return result

    def clear(self) -> None:
        self._ownerships.clear()
        self._permissions.clear()
