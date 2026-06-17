from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreatePasswordsFromKeepassCommand:
    user_id: UUID
    group_id: UUID
    filename: str
    content: bytes
    master_password: str
