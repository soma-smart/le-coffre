from uuid import UUID


class FakeGroupAccessGateway:
    """Fake implementation of GroupAccessGateway for testing"""

    def __init__(self):
        self._group_owners: dict[UUID, UUID] = {}  # group_id -> user_id
        self._group_members: dict[UUID, list[UUID]] = {}  # group_id -> list of user_ids

    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        """Check if user owns the group"""
        return self._group_owners.get(group_id) == user_id

    def is_user_member_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        return user_id in self._group_members.get(group_id, [])

    def group_exists(self, group_id: UUID) -> bool:
        """Check if group exists"""
        return group_id in self._group_owners

    def get_group_owner_users(self, group_id: UUID) -> list[UUID]:
        """Get all users who own this group"""
        # For testing purposes, return the list of members if available, otherwise the single owner
        if group_id in self._group_members:
            return self._group_members[group_id]
        elif group_id in self._group_owners:
            return [self._group_owners[group_id]]
        return []

    def set_group_owner(self, group_id: UUID, user_id: UUID) -> None:
        """Test helper to setup ownership"""
        self._group_owners[group_id] = user_id
        # Also add to members list
        if group_id not in self._group_members:
            self._group_members[group_id] = []
        if user_id not in self._group_members[group_id]:
            self._group_members[group_id].append(user_id)

    def add_group_member(self, group_id: UUID, user_id: UUID) -> None:
        """Test helper to add a member to a group"""
        if group_id not in self._group_members:
            self._group_members[group_id] = []
        if user_id not in self._group_members[group_id]:
            self._group_members[group_id].append(user_id)

    def clear(self) -> None:
        """Test helper to clear all data"""
        self._group_owners.clear()
        self._group_members.clear()
