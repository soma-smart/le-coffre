from dataclasses import dataclass
from uuid import UUID
from typing import Optional


@dataclass
class CreateUserCommand:
    id: UUID
    username: str
    email: str
    name: str
    password: Optional[str] = None
