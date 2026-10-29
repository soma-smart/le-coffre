from dataclasses import dataclass
from uuid import UUID


@dataclass
class RemoveUserFromGroupCommand:
    requester_id: UUID
    group_id: UUID
    user_id: UUID
