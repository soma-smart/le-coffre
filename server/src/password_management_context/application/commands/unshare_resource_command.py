from uuid import UUID
from dataclasses import dataclass


@dataclass
class UnshareResourceCommand:
    owner_id: UUID
    user_id: UUID
    password_id: UUID
