from dataclasses import dataclass
from uuid import UUID


@dataclass
class GroupResponse:
    id: UUID
    name: str
    is_personal: bool
    user_id: UUID | None
    owners: list[UUID]
    members: list[UUID]


@dataclass
class ListGroupResponse:
    groups: list[GroupResponse]
