from typing import Dict, List, Optional
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError


class FakePasswordRepository(PasswordRepository):
    def __init__(self):
        self.storage: Dict[UUID, Password] = {}
        self._password_owners: Dict[UUID, UUID] = {}  # password_id -> owner_group_id
        self.update_count: int = 0

    def save(self, password: Password) -> None:
        self.storage[password.id] = password

    def get_by_id(self, id: UUID) -> Password:
        if id not in self.storage:
            raise PasswordNotFoundError(id)
        return self.storage[id]

    def list_all(self, folder: Optional[str] = None) -> List[Password]:
        if folder:
            return [p for p in self.storage.values() if p.folder == folder]
        return list(self.storage.values())

    def delete(self, id: UUID) -> None:
        if id not in self.storage:
            raise PasswordNotFoundError(id)
        del self.storage[id]
        if id in self._password_owners:
            del self._password_owners[id]

    def delete_by_owner_group(self, group_id: UUID) -> None:
        """Delete all passwords owned by a specific group"""
        password_ids_to_delete = [
            password_id for password_id, owner_id in self._password_owners.items() if owner_id == group_id
        ]
        for password_id in password_ids_to_delete:
            if password_id in self.storage:
                del self.storage[password_id]
            if password_id in self._password_owners:
                del self._password_owners[password_id]

    def update(self, password: Password) -> None:
        if password.id not in self.storage:
            raise PasswordNotFoundError(password.id)
        self.storage[password.id] = password
        self.update_count += 1

    def count(self) -> int:
        return len(self.storage)

    def set_owner_for_password(self, password_id: UUID, owner_group_id: UUID) -> None:
        """Helper method for tests to track ownership"""
        self._password_owners[password_id] = owner_group_id
