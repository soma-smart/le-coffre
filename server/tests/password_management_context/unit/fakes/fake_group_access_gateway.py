from uuid import UUID


class FakeGroupAccessGateway:
    """Fake implementation of GroupAccessGateway for testing.

    Owners and members are tracked as distinct sets, mirroring the real
    adapter: an owner is reported by get_group_owner_users, a non-owner
    member by get_group_member_users. An owner also counts as a member for
    access checks (owners have a membership row in production).
    """

    def __init__(self):
        self._group_owners: dict[UUID, set[UUID]] = {}  # group_id -> owner user_ids
        self._group_members: dict[UUID, set[UUID]] = {}  # group_id -> non-owner member user_ids
        self._groups_with_passwords: set[UUID] = set()  # group_ids that own passwords

    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        return user_id in self._group_owners.get(group_id, set())

    def is_user_member_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        return user_id in self._group_members.get(group_id, set()) or self.is_user_owner_of_group(user_id, group_id)

    def group_exists(self, group_id: UUID) -> bool:
        return group_id in self._group_owners or group_id in self._group_members

    def get_group_owner_users(self, group_id: UUID) -> list[UUID]:
        return list(self._group_owners.get(group_id, set()))

    def get_group_member_users(self, group_id: UUID) -> list[UUID]:
        return list(self._group_members.get(group_id, set()))

    def group_owns_passwords(self, group_id: UUID) -> bool:
        return group_id in self._groups_with_passwords

    def set_group_owner(self, group_id: UUID, user_id: UUID) -> None:
        """Test helper: register a user as an owner of the group."""
        self._group_owners.setdefault(group_id, set()).add(user_id)

    def add_group_member(self, group_id: UUID, user_id: UUID) -> None:
        """Test helper: register a user as a (non-owner) member of the group."""
        self._group_members.setdefault(group_id, set()).add(user_id)

    def add_group_with_passwords(self, group_id: UUID) -> None:
        """Test helper to simulate a group owning passwords"""
        self._groups_with_passwords.add(group_id)

    def remove_group_passwords(self, group_id: UUID) -> None:
        """Test helper to remove passwords from a group"""
        self._groups_with_passwords.discard(group_id)

    def clear(self) -> None:
        """Test helper to clear all data"""
        self._group_owners.clear()
        self._group_members.clear()
        self._groups_with_passwords.clear()
