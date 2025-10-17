from dataclasses import dataclass
from uuid import UUID


@dataclass
class CreateGroupResponse:
    group_id: UUID
