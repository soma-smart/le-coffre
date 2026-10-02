from typing import Dict
from uuid import UUID

from identity_access_management_context.domain.entities import GroupMember


class FakeGroupMemberRepository:
    def __init__(self):
        self._members: Dict[tuple[UUID, UUID], GroupMember] = {}

    def add_member(self, group_id: UUID, principal_id: UUID, is_owner: bool) -> None:
        key = (group_id, principal_id)
        self._members[key] = GroupMember(group_id=group_id, principal_id=principal_id, is_owner=is_owner)

    def remove_member(self, group_id: UUID, principal_id: UUID) -> None:
        key = (group_id, principal_id)
        if key in self._members:
            del self._members[key]

    def is_member(self, group_id: UUID, principal_id: UUID) -> bool:
        key = (group_id, principal_id)
        return key in self._members

    def is_owner(self, group_id: UUID, principal_id: UUID) -> bool:
        key = (group_id, principal_id)
        member = self._members.get(key)
        return member is not None and member.is_owner

    def get_members(self, group_id: UUID) -> list[GroupMember]:
        return [m for m in self._members.values() if m.group_id == group_id]

    def get_group_ids_owned_by(self, principal_id: UUID) -> list[UUID]:
        return [m.group_id for m in self._members.values() if m.principal_id == principal_id and m.is_owner]

    def count_owners(self, group_id: UUID) -> int:
        return sum(1 for m in self._members.values() if m.group_id == group_id and m.is_owner)

    def delete_by_group_id(self, group_id: UUID):
        self._members = {key: member for key, member in self._members.items() if member.group_id != group_id}

    def remove_principal_from_all_groups(self, principal_id: UUID) -> None:
        """Remove a user from all groups they belong to."""
        self._members = {key: member for key, member in self._members.items() if member.principal_id != principal_id}

    def clear(self) -> None:
        self._members.clear()
