from dataclasses import dataclass
from uuid import UUID


@dataclass
class UpdateUserPasswordCommand:
    user_id: UUID
    old_password: str
    new_password: str
