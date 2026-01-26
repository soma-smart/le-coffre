from dataclasses import dataclass
from uuid import UUID


@dataclass
class ListAccessCommand:
    requester_id: UUID
    password_id: UUID
