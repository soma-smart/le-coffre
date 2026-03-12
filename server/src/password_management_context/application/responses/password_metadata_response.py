from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PasswordMetadataResponse:
    id: UUID
    name: str
    folder: str
    group_id: UUID
    created_at: datetime
    last_password_updated_at: datetime
    can_read: bool
    can_write: bool
    login: str | None = None
    url: str | None = None
