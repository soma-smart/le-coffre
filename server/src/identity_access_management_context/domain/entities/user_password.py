from dataclasses import dataclass
from uuid import UUID


@dataclass
class UserPassword:
    id: UUID
    email: str
    password_hash: bytes
    display_name: str
