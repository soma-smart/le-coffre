from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PasswordResponse:
    id: UUID
    name: str
    password: str
    folder: str
    created_at: datetime | None
    last_password_updated_at: datetime | None
