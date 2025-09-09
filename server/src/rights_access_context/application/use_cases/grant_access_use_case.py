from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)
from rights_access_context.domain.value_objects.permission import Permission


class GrantAccessUseCase:
    def __init__(self, rights_repository: RightsRepository):
        self.rights_repository = rights_repository

    def execute(self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ) -> None:
        self.rights_repository.add_permission(user_id, resource_id, permission)
