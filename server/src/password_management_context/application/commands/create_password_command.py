from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreatePasswordCommand:
    user_id: UUID
    group_id: UUID
    id: UUID
    name: str
    decrypted_password: str
    folder: str | None = None
    login: str | None = None
    url: str | None = None
