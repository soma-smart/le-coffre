from dataclasses import dataclass
from uuid import UUID


@dataclass
class Group:
    id: UUID
    name: str
    is_personal: bool
    user_id: UUID | None = None
