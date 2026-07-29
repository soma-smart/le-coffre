from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class UpdateShareExpirationCommand:
    owner_id: UUID  # User requesting the change
    group_id: UUID  # Group whose share is being retimed
    password_id: UUID
    expires_at: datetime | None = None  # None makes the share permanent
