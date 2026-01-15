from uuid import UUID
from dataclasses import dataclass


@dataclass
class ShareResourceCommand:
    owner_id: UUID
    user_id: UUID
    password_id: UUID
