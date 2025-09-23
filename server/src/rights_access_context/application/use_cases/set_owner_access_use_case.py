from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)


class SetOwnerAccessUseCase:
    def __init__(self, rights_repository: RightsRepository):
        self.rights_repository = rights_repository

    def execute(
        self,
        user_id: UUID,
        resource_id: UUID,
    ) -> None:
        self.rights_repository.set_owner(user_id, resource_id)
