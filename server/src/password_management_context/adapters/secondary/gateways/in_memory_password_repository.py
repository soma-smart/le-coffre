from typing import Optional, Dict
from uuid import UUID

from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password


class InMemoryPasswordRepository(PasswordRepository):
    def __init__(self):
        self.storage: Dict[UUID, Password] = {}

    def save(self, password: Password) -> None:
        self.storage[password.id] = password

    def get_by_id(self, id: UUID) -> Password:
        if id not in self.storage:
            raise PasswordNotFoundError(f"Password with ID {id} not found")
        return self.storage[id]


class PasswordNotFoundError(Exception):
    pass
