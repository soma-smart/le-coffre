from typing import Protocol
from uuid import UUID
from user_management_context.domain.entities import User


class UserRepository(Protocol):
    def get_by_id(self, user_id: UUID) -> User:
        ...

    def get_by_email(self, email: str) -> User:
        ...

    def save(self, user: User) -> None:
        ...

    def delete(self, user_id: UUID) -> None:
        ...
