from uuid import UUID

from password_management_context.application.gateways import (
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.access_control import AccessResult, Granted


class CheckAccessUseCase:
    def __init__(self, permission_repository: PasswordPermissionsRepository):
        self.permission_repository = permission_repository

    def execute(
        self,
        user_id: UUID,
        resource_id: UUID,
        permission: PasswordPermission = PasswordPermission.READ,
    ) -> AccessResult:
        if self.permission_repository.is_owner(user_id, resource_id):
            return AccessResult(granted=Granted.ACCESS, is_owner=True)

        has_permission = self.permission_repository.has_access(
            user_id, resource_id, permission
        )

        if not has_permission:
            return AccessResult(granted=Granted.NOT_FOUND)

        return AccessResult(granted=Granted.ACCESS)
