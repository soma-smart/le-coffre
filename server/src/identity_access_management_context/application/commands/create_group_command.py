from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateGroupCommand:
    id: UUID
    name: str
    creator_id: UUID
