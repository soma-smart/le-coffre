from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class OneTimeLinkDetails:
    """What this context knows of a one-time link, as the password context reports it."""

    link_id: UUID
    created_by_user_id: UUID
    password_name: str
    expires_at: datetime
    read_at: datetime | None
    revoked_at: datetime | None

    def is_active(self, now: datetime) -> bool:
        return self.read_at is None and self.revoked_at is None and now < self.expires_at

    def expired_unused(self, now: datetime) -> bool:
        return self.read_at is None and self.revoked_at is None and now >= self.expires_at
