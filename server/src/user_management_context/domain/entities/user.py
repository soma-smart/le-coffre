from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class User:
    id: UUID
    username: str
    email: str
    password_hashed: str
