from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class IsGroupUsedCommand:
    group_id: UUID
