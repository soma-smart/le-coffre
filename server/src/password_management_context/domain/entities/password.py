from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class Password:
    id: UUID
    name: str
    encrypted_value: str
    folder: Optional[str] = None
