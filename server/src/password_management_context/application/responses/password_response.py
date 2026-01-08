from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PasswordResponse:
    id: UUID
    name: str
    password: str
    folder: str
