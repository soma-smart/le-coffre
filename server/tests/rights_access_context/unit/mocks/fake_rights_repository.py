from uuid import UUID

from rights_access_context.application.gateways import (
    RightsRepository,
)


class FakeRightsRepository(RightsRepository):
    def __init__(self):
        self.owned_passwords = {}

    def add_ownership(self, user_id: UUID, password_id: UUID):
        self.owned_passwords[f"{user_id}:{password_id}"] = True

    def is_owner(self, user_id: UUID, password_id: UUID) -> bool:
        return self.owned_passwords.get(f"{user_id}:{password_id}", False)
    
    def has_access(self, user_id, resource_id):
        return self.owned_passwords.get(f"{user_id}:{resource_id}", False)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.owned_passwords[f"{user_id}:{resource_id}"] = True
