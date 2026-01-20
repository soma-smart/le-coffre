from typing import Dict
from uuid import UUID

from identity_access_management_context.domain.entities import PersonalGroup, Group


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

    def clear(self) -> None:
        self._groups.clear()
