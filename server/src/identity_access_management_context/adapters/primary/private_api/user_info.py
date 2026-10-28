from dataclasses import dataclass
from uuid import UUID

from identity_access_management_context.application.commands import (
    GetGroupCommand,
    GetPrincipalCommand,
    GetUserCommand,
)
from identity_access_management_context.application.use_cases import (
    GetGroupUseCase,
    GetPrincipalUseCase,
    GetUserUseCase,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotFoundError,
)


@dataclass(frozen=True)
class PrincipalInfo:
    """How another context may name a principal: its kind and display name."""

    kind: str
    """`user` or `service_account`."""
    display_name: str


class UserInfoApi:
    """Private API for other bounded contexts to query user information.

    This API provides a controlled interface to user data without exposing
    internal implementation details like repositories or database models.
    """

    def __init__(
        self,
        get_user_use_case: GetUserUseCase,
        get_group_use_case: GetGroupUseCase,
        get_principal_use_case: GetPrincipalUseCase,
    ):
        self._get_user_use_case = get_user_use_case
        self._get_group_use_case = get_group_use_case
        self._get_principal_use_case = get_principal_use_case

    def get_principal_info(self, principal_id: UUID) -> PrincipalInfo | None:
        """Name a principal of any kind, or None if it no longer exists."""
        response = self._get_principal_use_case.execute(GetPrincipalCommand(principal_id=principal_id))
        if response is None:
            return None
        return PrincipalInfo(kind=response.kind, display_name=response.display_name)

    def get_user_display_name(self, user_id: UUID) -> str | None:
        """Get the display name for a user.

        Args:
            user_id: The ID of the user

        Returns:
            The user's display name, or None if user not found
        """
        try:
            command = GetUserCommand(user_id=user_id)
            user = self._get_user_use_case.execute(command)
            return user.name
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
