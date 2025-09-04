from typing import Protocol, Optional
from uuid import UUID

from authentication_context.domain.entities import AdminAccount


class AdminRepository(Protocol):
    def save(self, admin: AdminAccount) -> None:
        """Save an admin account to the repository"""
        ...

    def get_by_id(self, admin_id: UUID) -> Optional[AdminAccount]:
        """Get an admin account by ID"""
        ...

    def get_by_email(self, email: str) -> Optional[AdminAccount]:
        """Get an admin account by email"""
        ...

    def exists_any(self) -> bool:
        """Check if any admin account exists"""
        ...
