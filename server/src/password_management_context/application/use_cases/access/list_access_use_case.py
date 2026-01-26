from uuid import UUID

from password_management_context.application.commands import ListAccessCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.application.responses import (
    ListAccessResponse,
    GroupAccessResponse,
    UserAccessResponse,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.value_objects import PasswordPermission


class ListAccessUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def execute(self, command: ListAccessCommand) -> ListAccessResponse:
        password_data = self.password_repository.get_by_id(command.password_id)
        if not password_data:
            raise PasswordNotFoundError(command.password_id)

        # Check if user has access through their groups
        if not self._user_has_access_through_groups(
            command.requester_id, command.password_id
        ):
            raise PasswordAccessDeniedError(command.requester_id, command.password_id)

        permissions = self.password_permissions_repository.list_all_permissions_for(
            command.password_id
        )

        # Expand groups to users for the access list
        ret = ListAccessResponse([], [])
        user_access_map = {}  # user_id -> (is_owner, permissions)

        for group_id, (is_group_owner, group_permissions) in permissions.items():
            ret.group_accesses.append(
                GroupAccessResponse(
                    group_id=group_id,
                    permissions=group_permissions,
                    is_owner=is_group_owner,
                )
            )

            # Get all users who own this group
            owner_users = self.group_access_gateway.get_group_owner_users(group_id)

            for user_id in owner_users:
                if user_id not in user_access_map:
                    # First time seeing this user, set their ownership status
                    user_access_map[user_id] = (is_group_owner, group_permissions)
                else:
                    # User already in map, merge permissions and maintain owner status
                    existing_is_owner, existing_perms = user_access_map[user_id]
                    # User is owner if they're owner through ANY group
                    merged_is_owner = existing_is_owner or is_group_owner
                    # Merge permissions
                    merged_perms = existing_perms | group_permissions
                    user_access_map[user_id] = (merged_is_owner, merged_perms)

        # Convert map to list of UserAccessResponse
        for user_id, (is_owner, perms) in user_access_map.items():
            ret.user_accesses.append(
                UserAccessResponse(
                    user_id=user_id,
                    is_owner=is_owner,
                    permissions=set() if is_owner else perms,
                )
            )

        return ret

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user is owner or member of this group
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(
                user_id, group_id
            )
            is_user_member = self.group_access_gateway.is_user_member_of_group(
                user_id, group_id
            )

            if is_user_owner or is_user_member:
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return True

        return False
