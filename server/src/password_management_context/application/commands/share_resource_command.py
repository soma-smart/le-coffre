from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ShareResourceCommand:
    owner_id: UUID  # User requesting the share
    group_id: UUID  # Group to share with
    password_id: UUID
    expires_at: datetime | None = None  # None shares permanently
