from uuid import UUID, uuid4
from datetime import datetime, UTC, timedelta


class AuthenticationSession:
    def __init__(self, user_id: UUID, jwt_token: str, ttl_hours: int = 24):
        self.id = uuid4()
        self.user_id = user_id
        self.jwt_token = jwt_token
        self.created_at = datetime.now(UTC)
        self.expires_at = self.created_at + timedelta(hours=ttl_hours)

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at
