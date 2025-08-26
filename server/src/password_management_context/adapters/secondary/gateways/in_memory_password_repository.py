from typing import Dict, List, Optional
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import PasswordNotFoundError


class InMemoryPasswordRepository(PasswordRepository):
    def __init__(self):
        self.storage: Dict[UUID, Password] = {}

    def save(self, password: Password) -> None:
        self.storage[password.id] = password

    def get_by_id(self, id: UUID) -> Password:
        if id not in self.storage:
            raise PasswordNotFoundError(id)
        return self.storage[id]

    def list_all(self, folder: Optional[str] = None) -> List[Password]:
        return [p for p in self.storage.values() if p.folder == folder]

    def delete(self, id: UUID) -> None:
        if id not in self.storage:
            raise PasswordNotFoundError(id)
        del self.storage[id]
