from typing import Protocol, Optional
from uuid import UUID

from identity_access_management_context.domain.entities import UserPassword


class UserPasswordRepository(Protocol):
    def save(self, user_password: UserPassword) -> None:
        """Save a user password entry"""
        ...

    def get_by_id(self, id: UUID) -> Optional[UserPassword]:
        """Get user password by ID"""
        ...

    def get_by_email(self, email: str) -> Optional[UserPassword]:
        """Get user password by email"""
        ...
