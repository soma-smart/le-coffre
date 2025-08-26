from typing import Protocol
from uuid import UUID


class RightsRepository(Protocol):
    def is_owner(self, user_id: UUID, password_id: UUID) -> bool: ...
