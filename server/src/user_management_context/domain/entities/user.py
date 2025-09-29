from dataclasses import dataclass, field
from uuid import UUID
from typing import List


@dataclass
class User:
    id: UUID
    username: str
    email: str
    name: str
    roles: List[str] = field(default_factory=list)
