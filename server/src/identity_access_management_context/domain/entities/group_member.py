from dataclasses import dataclass
from uuid import UUID


@dataclass
class GroupMember:
    group_id: UUID
    user_id: UUID
    is_owner: bool
