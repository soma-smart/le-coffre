from typing import Protocol
from uuid import UUID


class AccessController(Protocol):
    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        """Check if user has access to resource"""
        ...

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant access to a resource for a specific user"""
        ...
