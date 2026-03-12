from dataclasses import dataclass
from uuid import UUID


@dataclass
class UpdatePasswordCommand:
    requester_id: UUID
    id: UUID
    name: str
    password: str | None = None
    folder: str | None = None
    login: str | None = None
    url: str | None = None
