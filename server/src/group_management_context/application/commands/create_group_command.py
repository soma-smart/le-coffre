from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateGroupCommand:
    user_id: UUID
    name: str
    group_id: UUID
