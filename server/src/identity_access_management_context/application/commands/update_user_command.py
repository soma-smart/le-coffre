from dataclasses import dataclass
from uuid import UUID


@dataclass
class UpdateUserCommand:
    id: UUID
    username: str
    email: str
    name: str
