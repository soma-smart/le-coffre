from uuid import UUID
from dataclasses import dataclass


@dataclass
class ShareResourceCommand:
    owner_id: UUID  # User requesting the share
    group_id: UUID  # Group to share with
    password_id: UUID
