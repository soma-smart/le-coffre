from dataclasses import dataclass
from uuid import UUID


@dataclass
class GroupMember:
    group_id: UUID
    principal_id: UUID
    is_owner: bool
