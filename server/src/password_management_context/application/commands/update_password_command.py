from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class UpdatePasswordCommand:
    requester_id: UUID
    id: UUID
    name: str
    password: str
    folder: Optional[str] = None
