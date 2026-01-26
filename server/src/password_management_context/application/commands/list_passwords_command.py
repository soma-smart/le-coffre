from dataclasses import dataclass
from uuid import UUID


@dataclass
class ListPasswordsCommand:
    requester_id: UUID
    folder: str | None = None
