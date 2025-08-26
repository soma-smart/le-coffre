from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)
from rights_access_context.application.responses import AccessResult


class CheckAccessUseCase:
    def __init__(self, rights_repository: RightsRepository):
        self.rights_repository = rights_repository

    def execute(self, user_id: UUID, password_id: UUID) -> AccessResult:
        is_owner = self.rights_repository.is_owner(user_id, password_id)
        return AccessResult(granted=is_owner)
