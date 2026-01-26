from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetPasswordCommand:
    requester_id: UUID
    password_id: UUID
