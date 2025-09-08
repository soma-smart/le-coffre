from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)
from shared_kernel.access_control import AccessResult, Granted
from rights_access_context.domain.value_objects import Permission


class CheckAccessUseCase:
    def __init__(self, rights_repository: RightsRepository):
        self.rights_repository = rights_repository

    def execute(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> AccessResult:
        all_permissions = self.rights_repository.get_all_permissions(
            user_id, resource_id
        )

        if not all_permissions:
            return AccessResult(granted=Granted.NOT_FOUND)

        if permission in all_permissions:
            return AccessResult(granted=Granted.ACCESS)

        if Permission.READ in all_permissions:
            return AccessResult(granted=Granted.VIEW_ONLY)

        return AccessResult(granted=Granted.NOT_FOUND)
