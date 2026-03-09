from dataclasses import dataclass
from uuid import UUID


@dataclass
class ShareResourceCommand:
    owner_id: UUID  # User requesting the share
    group_id: UUID  # Group to share with
    password_id: UUID
