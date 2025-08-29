from uuid import UUID

from rights_access_context.application.gateways.rights_repository import (
    RightsRepository,
)


class InMemoryRightsRepository(RightsRepository):
    def __init__(self):
        self.rights = {}

    def grant_access(self, user_id: UUID, resource_id: UUID):
        self.rights[(user_id, resource_id)] = True

    def has_access(self, user_id: UUID, resource_id: UUID) -> bool:
        return self.rights.get((user_id, resource_id), False)
