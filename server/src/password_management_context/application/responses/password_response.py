from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PasswordResponse:
    id: UUID
    name: str
    password: str
    folder: str
    login: str | None
    url: str | None
    created_at: datetime
    last_password_updated_at: datetime
