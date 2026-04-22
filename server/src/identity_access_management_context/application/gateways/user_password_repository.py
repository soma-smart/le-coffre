from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import UserPassword


class UserPasswordRepository(Protocol):
    def save(self, user_password: UserPassword) -> None:
        """Save a user password entry"""
        ...

    def update_password(self, user_id: UUID, new_hashed_password: bytes) -> None:
        """Update an existing user password, password"""
        ...

    def get_by_id(self, id: UUID) -> UserPassword | None:
        """Get user password by ID"""
        ...

    def get_by_email(self, email: str) -> UserPassword | None:
        """Get user password by email"""
        ...

    def count(self) -> int:
        """Return total number of user passwords"""
        ...
