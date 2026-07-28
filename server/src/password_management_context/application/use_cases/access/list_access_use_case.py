from datetime import datetime, timedelta
from uuid import UUID

from password_management_context.application.commands import ListAccessCommand
from password_management_context.application.gateways import (
    GroupAccessGateway,
    PasswordPermissionsRepository,
    PasswordRepository,
)
from password_management_context.application.gateways.password_permissions_repository import (
    GroupPermissions,
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
from shared_kernel.application.gateways.time_gateway import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class ListAccessUseCase(TracedUseCase):
    """Lists who can reach a password, including shares that have already lapsed.

    Expired shares are deliberately still returned: their owner needs to see that
    an access ran out and be able to extend it. Callers deciding whether someone
    may *read* the password must not use this list as-is. That is what
    PasswordGroupAccess.grants_read is for.
    """

    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
        time_gateway: TimeGateway,
        expired_share_retention_seconds: int,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway
        self.time_gateway = time_gateway
        self.expired_share_retention_seconds = expired_share_retention_seconds

    def execute(self, command: ListAccessCommand) -> ListAccessResponse:
        password_data = self.password_repository.get_by_id(command.password_id)
        if not password_data:
            raise PasswordNotFoundError(command.password_id)

        now = self.time_gateway.get_current_time()

        # There is no scheduler in this application, so long-dead shares are
        # dropped here, on the one screen that reads them. Same pattern as
        # AuthSessionRepository.purge_dead being driven by the refresh flow.
        self.password_permissions_repository.purge_expired_shares(
            now - timedelta(seconds=self.expired_share_retention_seconds)
        )

        permissions = self.password_permissions_repository.list_all_permissions_for(command.password_id)

        if not self._user_has_access_through_groups(command.requester_id, permissions, now):
            raise PasswordAccessDeniedError(command.requester_id, command.password_id)

        user_accesses: list[UserAccessResponse] = []
        group_accesses: list[GroupAccessResponse] = []

        for group_id, access in permissions.items():
            group_role = AccessRole.OWNER if access.is_owner else AccessRole.MEMBER

            group_accesses.append(
                GroupAccessResponse(
                    group_id=group_id,
                    role=group_role,
                    permissions=access.permissions,
                    expires_at=access.expires_at,
                )
            )

            for owner_user_id in self.group_access_gateway.get_group_owner_users(group_id):
                user_accesses.append(
                    self._link(
                        owner_user_id, group_id, AccessRole.OWNER, group_role, access.permissions, access.expires_at
                    )
                )

            for member_user_id in self.group_access_gateway.get_group_member_users(group_id):
                user_accesses.append(
                    self._link(
                        member_user_id, group_id, AccessRole.MEMBER, group_role, access.permissions, access.expires_at
                    )
                )

        return ListAccessResponse(user_accesses, group_accesses)

    @staticmethod
    def _link(
        user_id: UUID,
        group_id: UUID,
        role_in_group: AccessRole,
        group_role: AccessRole,
        permissions: set[PasswordPermission],
        expires_at: datetime | None,
    ) -> UserAccessResponse:
        return UserAccessResponse(
            user_id=user_id,
            group_id=group_id,
            role_in_group=role_in_group,
            group_role=group_role,
            permissions=permissions,
            expires_at=expires_at,
        )

    def _user_has_access_through_groups(self, user_id: UUID, permissions: GroupPermissions, now: datetime) -> bool:
        """Check if user still has live access to password through any of their groups"""
        for group_id, access in permissions.items():
            if not access.grants_read(now):
                continue

            is_user_owner = self.group_access_gateway.is_user_owner_of_group(user_id, group_id)
            is_user_member = self.group_access_gateway.is_user_member_of_group(user_id, group_id)

            if is_user_owner or is_user_member:
                return True

        return False
