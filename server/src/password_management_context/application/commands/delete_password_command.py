from dataclasses import dataclass
from uuid import UUID


@dataclass
class DeletePasswordCommand:
    requester_id: UUID
    password_id: UUID
