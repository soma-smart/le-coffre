from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass
class SsoUser:
    internal_user_id: UUID
    email: str
    display_name: str
    sso_user_id: str
    sso_provider: str = "default"
    created_at: datetime | None = None
    last_login: datetime | None = None
