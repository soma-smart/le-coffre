from uuid import UUID

from password_management_context.application.commands import ListAccessCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.responses import (
    GroupAccessResponse,
    ListAccessResponse,
    UserAccessResponse,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import AccessRole, PasswordPermission
from shared_kernel.application.tracing import TracedUseCase


class ListAccessUseCase(TracedUseCase):
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

        if not self._user_has_access_through_groups(command.requester_id, command.password_id):
            raise PasswordAccessDeniedError(command.requester_id, command.password_id)

        permissions = self.password_permissions_repository.list_all_permissions_for(command.password_id)

        user_accesses: list[UserAccessResponse] = []
        group_accesses: list[GroupAccessResponse] = []

        for group_id, (is_group_owner, group_permissions) in permissions.items():
            group_role = AccessRole.OWNER if is_group_owner else AccessRole.MEMBER

            group_accesses.append(
                GroupAccessResponse(
                    group_id=group_id,
                    role=group_role,
                    permissions=group_permissions,
                )
            )

            for owner_user_id in self.group_access_gateway.get_group_owner_users(group_id):
                user_accesses.append(
                    self._link(owner_user_id, group_id, AccessRole.OWNER, group_role, group_permissions)
                )

            for member_user_id in self.group_access_gateway.get_group_member_users(group_id):
                user_accesses.append(
                    self._link(member_user_id, group_id, AccessRole.MEMBER, group_role, group_permissions)
                )

        return ListAccessResponse(user_accesses, group_accesses)

    @staticmethod
    def _link(
        user_id: UUID,
        group_id: UUID,
        role_in_group: AccessRole,
        group_role: AccessRole,
        permissions: set[PasswordPermission],
    ) -> UserAccessResponse:
        return UserAccessResponse(
            user_id=user_id,
            group_id=group_id,
            role_in_group=role_in_group,
            group_role=group_role,
            permissions=permissions,
        )

    def _user_has_access_through_groups(self, user_id: UUID, password_id: UUID) -> bool:
        """Check if user has access to password through any of their groups"""
        all_permissions = self.password_permissions_repository.list_all_permissions_for(password_id)

        for group_id, (is_owner, permissions) in all_permissions.items():
            is_user_owner = self.group_access_gateway.is_user_owner_of_group(user_id, group_id)
            is_user_member = self.group_access_gateway.is_user_member_of_group(user_id, group_id)

            if is_user_owner or is_user_member:
                if is_owner or PasswordPermission.READ in permissions:
                    return True

        return False
