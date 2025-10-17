from group_management_context.domain.group import Group
from uuid import UUID
from typing import Optional


class FakeGroupRepository:
    def __init__(self):
        self._groups: dict[UUID, Group] = {}

    def save(self, group: Group) -> None:
        self._groups[group.id] = group

    def exists_by_name(self, name: str) -> bool:
        return any(group.name == name for group in self._groups.values())

    def get_by_id(self, group_id: UUID) -> Optional[Group]:
        return self._groups.get(group_id)
