from typing import Protocol
from uuid import UUID


class UserManagementGateway(Protocol):
    def user_exists(self, user_id: UUID) -> bool: ...
