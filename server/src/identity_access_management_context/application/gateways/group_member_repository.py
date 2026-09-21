from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import GroupMember


class GroupMemberRepository(Protocol):
    def add_member(self, group_id: UUID, user_id: UUID, is_owner: bool) -> None:
        """Add a member to a group."""
        ...

    def remove_member(self, group_id: UUID, user_id: UUID) -> None:
        """Remove a member from a group."""
        ...

    def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        """Check if a user is a member of a group."""
        ...

    def is_owner(self, group_id: UUID, user_id: UUID) -> bool:
        """Check if a user is an owner of a group."""
        ...

    def get_members(self, group_id: UUID) -> list[GroupMember]:
        """Get all members of a group."""
        ...

    def count_owners(self, group_id: UUID) -> int:
        """Count the number of owners in a group."""
        ...

    def count_owners_for_update(self, group_id: UUID) -> int:
        """Count the number of owners in a group, locking those owner rows
        for the rest of the current transaction.

        Use this instead of count_owners() immediately before a write whose
        correctness depends on that count not changing before the write
        commits (e.g. refusing to demote the last owner) — a plain SELECT
        followed by a later write is a check-then-act race: two concurrent
        callers can both read the same count before either writes, and both
        proceed. The row lock serializes them: a second transaction's read
        blocks until the first commits, then re-evaluates against the
        now-current data.
        """
        ...

    def delete_by_group_id(self, group_id: UUID) -> None:
        """Delete all members of a group."""
        ...

    def remove_user_from_all_groups(self, user_id: UUID) -> None:
        """Remove a user from all groups they belong to."""
        ...
