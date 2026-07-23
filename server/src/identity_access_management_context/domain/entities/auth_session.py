from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class AuthSession:
    id: UUID
    user_id: UUID
    current_refresh_token_jti: str
    created_at: datetime
    updated_at: datetime
    invalidated_at: datetime | None = None
