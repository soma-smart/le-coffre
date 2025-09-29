from typing import Protocol
from uuid import UUID
from .access_result import AccessResult


class AccessController(Protocol):
    def check_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has access to resource"""
        ...

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant access to a resource for a specific user"""
        ...

    def check_update_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has update access to resource"""
        ...

    def grant_update_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant update access to a resource for a specific user"""
        ...

    def check_delete_access(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        """Check if user has delete access to resource"""
        ...

    def grant_delete_access(self, user_id: UUID, resource_id: UUID) -> None:
        """Grant delete access to a resource for a specific user"""
        ...

    def set_owner(self, user_id: UUID, resource_id: UUID) -> None:
        """Set the owner of a resource"""
        ...

    def is_owner(self, user_id: UUID, resource_id: UUID) -> bool:
        """Check if the user is the owner of the resource"""
        ...
