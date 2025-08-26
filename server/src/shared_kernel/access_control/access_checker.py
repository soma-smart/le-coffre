from typing import Protocol
from uuid import UUID


class AccessChecker(Protocol):
    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        """Check if user has access to resource for given action"""
        ...
