from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateOneTimeLinkCommand:
    password_id: UUID
    requesting_user_id: UUID
    lifetime_seconds: int | None = None  # None falls back to the domain default
    notify_on_read: bool = False  # email the creator when the link is read
    notify_on_expiry: bool = False  # email the creator if the link expires unread
