from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class CreatePasswordCommand:
    user_id: UUID
    group_id: UUID
    id: UUID
    name: str
    decrypted_password: str
    folder: Optional[str] = None
