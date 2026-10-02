from dataclasses import dataclass
from uuid import UUID


@dataclass
class AddOwnerToGroupCommand:
    requester_id: UUID
    group_id: UUID
    principal_id: UUID
