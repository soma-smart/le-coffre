from uuid import UUID
from dataclasses import dataclass


@dataclass
class ShareResourceCommand:
    owner_id: UUID
    user_id: UUID
    resource_id: UUID
