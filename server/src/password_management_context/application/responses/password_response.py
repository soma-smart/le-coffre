from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class PasswordResponse:
    id: UUID
    name: str
    password: str
    folder: Optional[str] = None
