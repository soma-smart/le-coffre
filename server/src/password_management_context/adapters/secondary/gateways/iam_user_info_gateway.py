from uuid import UUID

from identity_access_management_context.adapters.primary.private_api import (
    UserInfoApi,
)
from password_management_context.application.gateways.user_info_gateway import PrincipalInfo


class IamUserInfoGateway:
    """Gateway implementation to retrieve user information from IAM context.

    This adapter lives in the Password Management context and uses IAM's
    Private API to maintain bounded context isolation.
    """

    def __init__(self, user_info_api: UserInfoApi):
        self._user_info_api = user_info_api

    def get_principal(self, principal_id: UUID) -> PrincipalInfo | None:
        """Name a principal of any kind, or None if it no longer exists."""
        info = self._user_info_api.get_principal_info(principal_id)
        if info is None:
            return None
        return PrincipalInfo(kind=info.kind, display_name=info.display_name)

    def get_user_display_name(self, user_id: UUID) -> str | None:
        """Get the display name for a user.

        Args:
            user_id: The ID of the user

        Returns:
            The user's display name, or None if user not found
        """
        return self._user_info_api.get_user_display_name(user_id)

    def get_group_name(self, group_id: UUID) -> str | None:
        """Get name for a group.

        Args:
            group_id: The ID of the group

        Returns:
            The group's name, or None if group not found
        """
        return self._user_info_api.get_group_name(group_id)
