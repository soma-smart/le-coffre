from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class UpdatePasswordCommand:
    requester_id: UUID
    id: UUID
    name: Optional[str] = None
    password: Optional[str] = None
    folder: Optional[str] = None
