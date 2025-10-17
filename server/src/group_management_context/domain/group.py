from dataclasses import dataclass
from uuid import UUID


@dataclass
class Group:
    id: UUID
    name: str
    owner_id: UUID
