from dataclasses import dataclass
from uuid import UUID


@dataclass
class GetGroupCommand:
    group_id: UUID
