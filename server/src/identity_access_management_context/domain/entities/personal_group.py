from dataclasses import dataclass
from uuid import UUID


@dataclass
class PersonalGroup:
    id: UUID
    name: str
    principal_id: UUID
