from typing import Protocol
from uuid import UUID


class RightsRepository(Protocol):
    def grant_access(self, user_id: UUID, resource_id: UUID) -> None: ...
    def has_access(self, user_id: UUID, resource_id: UUID) -> bool: ...
