from typing import Optional, Protocol
from uuid import UUID

from password_management_context.domain.entities import Password


class PasswordRepository(Protocol):
    def save(self, password: Password) -> None:
        """Save a password entity"""
        ...

    def get_by_id(self, id: UUID) -> Password:
        """Get password by UUID - returns entity with encrypted value"""
        ...
