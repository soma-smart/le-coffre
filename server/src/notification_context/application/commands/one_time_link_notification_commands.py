from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class SubscribeToOneTimeLinkCommand:
    link_id: UUID
    user_id: UUID
    notify_on_read: bool
    notify_on_expiry: bool


@dataclass
class NotifyOneTimeLinkReadCommand:
    link_id: UUID
    password_name: str
    read_at: datetime
