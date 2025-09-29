from typing import List, Optional, Protocol
from uuid import UUID

from password_management_context.domain.entities import Password


class PasswordRepository(Protocol):
    def save(self, password: Password) -> None:
        """Save a password entity"""
        ...

    def get_by_id(self, id: UUID) -> Password:
        """Get password by UUID"""
        ...

    def list_all(self, folder: Optional[str] = None) -> List[Password]:
        """List all passwords"""
        ...

    def delete(self, id: UUID) -> None:
        """Delete password by UUID"""
        ...

    def update(self, password: Password) -> None:
        """Update password"""
        ...
