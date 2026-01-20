from uuid import UUID

from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
)


class GroupAccessGatewayAdapter:
    """Adapter implementing the GroupAccessGateway interface from Password Management context.

    This adapter allows the Password Management context to verify group ownership
    without creating a direct dependency on the IAM context.
    """

    def __init__(
        self,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ):
        self._group_repository = group_repository
        self._group_member_repository = group_member_repository

    def is_user_owner_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        """Check if a user is the owner of a group.

        Args:
            user_id: The ID of the user to check
            group_id: The ID of the group to check

        Returns:
            True if the user owns the group, False otherwise
        """
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return False

        # For personal groups, check if the user_id matches
        if group.is_personal and group.user_id == user_id:
            return True

        # For shared groups, check membership
        return self._group_member_repository.is_owner(group_id, user_id)

    def is_user_member_of_group(self, user_id: UUID, group_id: UUID) -> bool:
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return False

        # For personal groups, check if the user_id matches
        if group.is_personal and group.user_id == user_id:
            return True

        # For shared groups, check membership
        return self._group_member_repository.is_member(group_id, user_id)

    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists.

        Args:
            group_id: The ID of the group to check

        Returns:
            True if the group exists, False otherwise
        """
        return self._group_repository.get_by_id(group_id) is not None

    def get_group_owner_users(self, group_id: UUID) -> list[UUID]:
        """Get all users who own this group.

        Args:
            group_id: The ID of the group

        Returns:
            List of user IDs who own this group
        """
        group = self._group_repository.get_by_id(group_id)
        if group is None:
            return []

        # For personal groups, return the user_id
        if group.is_personal and group.user_id:
            return [group.user_id]

        # For shared groups, get all owner members
        members = self._group_member_repository.get_members(group_id)
        return [member.user_id for member in members if member.is_owner]
