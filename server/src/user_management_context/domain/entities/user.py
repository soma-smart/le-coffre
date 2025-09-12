from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class Resource:
    id: UUID

    def __init__(self, id: UUID = uuid4()):
        self.id = id


@dataclass
class User:
    id: UUID
    username: str
    email: str
    password_hashed: str
