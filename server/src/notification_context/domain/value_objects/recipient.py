from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Recipient:
    user_id: UUID
    email: str
    display_name: str
