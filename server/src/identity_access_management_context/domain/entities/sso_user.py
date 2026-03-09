from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SsoUser:
    internal_user_id: UUID
    email: str
    display_name: str
    sso_user_id: str
    sso_provider: str = "default"
    created_at: datetime | None = None
    last_login: datetime | None = None
