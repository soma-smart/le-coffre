from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import GroupMember


class GroupMemberRepository(Protocol):
    def add_member(self, group_id: UUID, principal_id: UUID, is_owner: bool) -> None:
        """Add a member to a group."""
        ...

    def remove_member(self, group_id: UUID, principal_id: UUID) -> None:
        """Remove a member from a group."""
        ...

    def is_member(self, group_id: UUID, principal_id: UUID) -> bool:
        """Check if a principal is a member of a group."""
        ...

    def is_owner(self, group_id: UUID, principal_id: UUID) -> bool:
        """Check if a principal is an owner of a group."""
        ...

    def get_members(self, group_id: UUID) -> list[GroupMember]:
        """Get all members of a group."""
        ...

    def get_group_ids_owned_by(self, principal_id: UUID) -> list[UUID]:
        """Return the ids of every group this principal owns."""
        ...

    def count_owners(self, group_id: UUID) -> int:
        """Count the number of owners in a group."""
        ...

    def delete_by_group_id(self, group_id: UUID) -> None:
        """Delete all members of a group."""
        ...

    def remove_principal_from_all_groups(self, principal_id: UUID) -> None:
        """Remove a principal from all groups it belongs to."""
        ...
