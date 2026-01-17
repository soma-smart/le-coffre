from uuid import UUID

from identity_access_management_context.application.gateways import GroupRepository


class GroupAccessGatewayAdapter:
    """Adapter implementing the GroupAccessGateway interface from Password Management context.

    This adapter allows the Password Management context to verify group ownership
    without creating a direct dependency on the IAM context.
    """

    def __init__(self, group_repository: GroupRepository):
        self._group_repository = group_repository

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
        return group.user_id == user_id

    def group_exists(self, group_id: UUID) -> bool:
        """Check if a group exists.

        Args:
            group_id: The ID of the group to check

        Returns:
            True if the group exists, False otherwise
        """
        return self._group_repository.get_by_id(group_id) is not None
