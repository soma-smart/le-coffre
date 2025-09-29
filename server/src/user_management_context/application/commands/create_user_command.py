from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class CreateUserCommand:
    id: UUID
    username: str
    email: str
    name: str
