from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import (
    UserInfoApi,
)


class IamUserInfoGateway:
    """Gateway implementation to retrieve user information from IAM context.

    This adapter lives in the Password Management context and uses IAM's
    Private API to maintain bounded context isolation.
    """

    def __init__(self, user_info_api: UserInfoApi):
        self._user_info_api = user_info_api

    def get_user_email(self, user_id: UUID) -> str | None:
        """Get email address for a user.

        Args:
            user_id: The ID of the user

        Returns:
            The user's email address, or None if user not found
        """
        return self._user_info_api.get_user_email(user_id)

    def get_group_name(self, group_id: UUID) -> str | None:
        """Get name for a group.

        Args:
            group_id: The ID of the group

        Returns:
            The group's name, or None if group not found
        """
        return self._user_info_api.get_group_name(group_id)
