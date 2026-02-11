from uuid import UUID

from identity_access_management_context.application.use_cases import (
    GetUserUseCase,
    GetGroupUseCase,
)
from identity_access_management_context.application.commands import (
    GetUserCommand,
    GetGroupCommand,
)
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
    GroupNotFoundException,
)


class UserInfoApi:
    """Private API for other bounded contexts to query user information.

    This API provides a controlled interface to user data without exposing
    internal implementation details like repositories or database models.
    """

    def __init__(
        self, get_user_use_case: GetUserUseCase, get_group_use_case: GetGroupUseCase
    ):
        self._get_user_use_case = get_user_use_case
        self._get_group_use_case = get_group_use_case

    def get_user_email(self, user_id: UUID) -> str | None:
        """Get email address for a user.

        Args:
            user_id: The ID of the user

        Returns:
            The user's email address, or None if user not found
        """
        try:
            command = GetUserCommand(user_id=user_id)
            user = self._get_user_use_case.execute(command)
            return user.email
        except UserNotFoundError:
            return None

    def get_group_name(self, group_id: UUID) -> str | None:
        """Get name for a group.

        Args:
            group_id: The ID of the group

        Returns:
            The group's name, or None if group not found
        """
        try:
            command = GetGroupCommand(group_id=group_id)
            response = self._get_group_use_case.execute(command)
            return response.group.name
        except GroupNotFoundException:
            return None
