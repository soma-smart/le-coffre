from typing import Dict
from uuid import UUID

from identity_access_management_context.domain.entities import Group, PersonalGroup


class FakeGroupRepository:
    def __init__(self):
        self._groups: Dict[UUID, Group] = {}

    def save_personal_group(self, group: PersonalGroup) -> None:
        # Store as a Group with user_id
        self._groups[group.id] = Group(
            id=group.id,
            name=group.name,
            is_personal=True,
            user_id=group.user_id,
        )

    def get_by_id(self, group_id: UUID) -> Group | None:
        return self._groups.get(group_id)

    def get_by_user_id(self, user_id: UUID) -> PersonalGroup | None:
        for group in self._groups.values():
            if group.is_personal and group.user_id == user_id:
                return PersonalGroup(
                    id=group.id,
                    name=group.name,
                    user_id=group.user_id,  # type: ignore - we know it's not None
                )
        return None

    def get_all(self) -> list[Group]:
        return list(self._groups.values())

    def save_group(self, group: Group) -> None:
        self._groups[group.id] = group

    def delete_group(self, group_id: UUID) -> None:
        if group_id in self._groups:
            del self._groups[group_id]

    def get_by_name(self, group_name: str) -> Group | None:
        for group in self._groups.values():
            if group.name == group_name:
                return group
        return None

    def clear(self) -> None:
        self._groups.clear()

    def get_number_of_groups_not_personal(self) -> int:
        return len([group for group in self._groups.values() if not group.is_personal])
