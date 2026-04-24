from typing import Protocol
from uuid import UUID

from password_management_context.domain.entities import Password


class PasswordRepository(Protocol):
    def save(self, password: Password) -> None:
        """Save a password entity"""
        ...

    def get_by_id(self, id: UUID) -> Password:
        """Get password by UUID"""
        ...

    def list_all(self, folder: str | None = None) -> list[Password]:
        """List all passwords"""
        ...

    def delete(self, id: UUID) -> None:
        """Delete password by UUID"""
        ...

    def delete_by_owner_group(self, group_id: UUID) -> None:
        """Delete all passwords owned by a specific group"""
        ...

    def update(self, password: Password) -> None:
        """Update password"""
        ...

    def count(self) -> int:
        """Count total number of passwords"""
        ...
