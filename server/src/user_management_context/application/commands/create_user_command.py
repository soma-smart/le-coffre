from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateUserCommand:
    id: UUID
    username: str
    email: str
    password: str
