from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class CreatePasswordCommand:
    id: UUID
    name: str
    decrypted_password: str
    folder: Optional[str] = None
