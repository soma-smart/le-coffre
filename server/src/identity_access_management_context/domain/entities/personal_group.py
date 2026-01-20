from dataclasses import dataclass
from uuid import UUID


@dataclass
class PersonalGroup:
    id: UUID
    name: str
    user_id: UUID
