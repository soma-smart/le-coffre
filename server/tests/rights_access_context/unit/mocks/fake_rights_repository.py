from uuid import UUID

from rights_access_context.adapters.secondary import (
    InMemoryRightsRepository,
)


class FakeRightsRepository(InMemoryRightsRepository):
    def __init__(self):
        self.owned_resources = {}

    def has_access(self, user_id, resource_id):
        return self.owned_resources.get(f"{user_id}:{resource_id}", False)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.owned_resources[f"{user_id}:{resource_id}"] = True
