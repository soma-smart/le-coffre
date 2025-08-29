from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)
from rights_access_context.application.responses import AccessResult


class CheckAccessUseCase:
    def __init__(self, rights_repository: RightsRepository):
        self.rights_repository = rights_repository

    def execute(self, user_id: UUID, resource_id: UUID) -> AccessResult:
        is_owner = self.rights_repository.has_access(user_id, resource_id)
        return AccessResult(granted=is_owner)
