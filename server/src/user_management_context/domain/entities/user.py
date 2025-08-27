from dataclasses import dataclass
from uuid import UUID


@dataclass
class User:
    id: UUID
    username: str
    email: str
    password_hashed: str
