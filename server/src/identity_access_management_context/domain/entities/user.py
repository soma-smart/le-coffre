from dataclasses import dataclass, field
from uuid import UUID
from typing import List, Optional


@dataclass
class User:
    id: UUID
    username: str
    email: str
    name: str
    roles: List[str] = field(default_factory=list)
    password_hash: Optional[str] = None
