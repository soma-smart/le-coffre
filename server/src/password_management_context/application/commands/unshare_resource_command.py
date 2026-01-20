from uuid import UUID
from dataclasses import dataclass


@dataclass
class UnshareResourceCommand:
    owner_id: UUID  # User requesting the unshare
    group_id: UUID  # Group to unshare from
    password_id: UUID
