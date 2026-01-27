from typing import Dict, List, Optional
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError


class FakePasswordRepository(PasswordRepository):
    def __init__(self):
        self.storage: Dict[UUID, Password] = {}

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

    def update(self, password: Password) -> None:
        if password.id not in self.storage:
            raise PasswordNotFoundError(password.id)
        self.storage[password.id] = password
