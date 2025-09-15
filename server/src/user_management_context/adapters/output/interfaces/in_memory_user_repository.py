from typing import Optional
from uuid import UUID
from user_management_context.application.interfaces import UserRepository
from user_management_context.domain.entities import User
from user_management_context.domain.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
)


class InMemoryUserRepository(UserRepository):
    def __init__(self):
        self.storage: dict[UUID, User] = {}

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.storage.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        for user in self.storage.values():
            if user.email == email:
                return user
        return None

    def list_all(self) -> list[User]:
        return list(self.storage.values())

    def save(self, user: User) -> None:
        if any(u.username == user.username for u in self.storage.values()):
            raise UserAlreadyExistsError(user.username)
        self.storage[user.id] = user

    def delete(self, user_id: UUID) -> None:
        if user_id not in self.storage:
            raise UserNotFoundError(user_id)
        del self.storage[user_id]

    def update(self, user: User) -> None:
        if user.id not in self.storage:
            raise UserNotFoundError(user.id)
        self.storage[user.id] = user

    def get_admin(self) -> Optional[User]:
        for user in self.storage.values():
            if "admin" in user.roles:
                return user

        return None
