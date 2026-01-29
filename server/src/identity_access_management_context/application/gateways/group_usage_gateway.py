from typing import Protocol
from uuid import UUID


class GroupUsageGateway(Protocol):
    def is_group_used(self, group_id: UUID) -> bool: ...
