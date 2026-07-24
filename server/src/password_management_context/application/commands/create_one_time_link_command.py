from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateOneTimeLinkCommand:
    password_id: UUID
    requesting_user_id: UUID
    lifetime_seconds: int | None = None  # None falls back to the domain default
