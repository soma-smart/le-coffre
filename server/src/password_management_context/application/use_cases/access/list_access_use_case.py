from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.application.responses import (
    ListAccessResponse,
    AccessResponse,
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

    def execute(self, requester_id: UUID, password_id: UUID) -> ListAccessResponse:
        password_data = self.password_repository.get_by_id(password_id)
        if not password_data:
            raise PasswordNotFoundError(password_id)

        # Check if user has access through their groups
        if not self._user_has_access_through_groups(requester_id, password_id):
            raise PasswordAccessDeniedError(requester_id, password_id)

        permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        # Return group-based access list
        ret = ListAccessResponse([])
        for group_id in permissions.keys():
            is_owner, group_permissions = permissions.get(group_id, (False, set()))
            ret.accesses.append(
                AccessResponse(
                    user_id=group_id,  # This is actually a group_id now
                    is_owner=is_owner,
                    permissions=group_permissions,
                )
            )

        return ret

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        for group_id, (is_owner, permissions) in all_permissions.items():
            # Check if user owns this group
            if self.group_access_gateway.is_user_owner_of_group(user_id, group_id):
                # If the group is the owner or has READ permission, user has access
                if is_owner or PasswordPermission.READ in permissions:
                    return True

        return False
