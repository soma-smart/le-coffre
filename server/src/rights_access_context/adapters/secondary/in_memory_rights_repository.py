from uuid import UUID
from typing import Dict, Set, Tuple

from rights_access_context.application.gateways import (
    RightsRepository,
)
from rights_access_context.domain.value_objects import Permission


class InMemoryRightsRepository(RightsRepository):
    def __init__(self):
        self.permissions: Dict[Tuple[UUID, UUID], Set[Permission]] = {}
        self.owned_resources: Dict[UUID, Set[UUID]] = {}

    def add_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> None:
        key = (user_id, resource_id)
        if key not in self.permissions:
            self.permissions[key] = set()
        self.permissions[key].add(permission)

    def has_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> bool:
        if self.is_owner(user_id, resource_id):
            return True
        key = (user_id, resource_id)
        return key in self.permissions and permission in self.permissions[key]

    def get_all_permissions(self, user_id: UUID, resource_id: UUID) -> set[Permission]:
        key = (user_id, resource_id)
        return self.permissions.get(key, set())

    def set_owner(self, user_id: UUID, resource_id: UUID) -> None:
        if user_id not in self.owned_resources:
            self.owned_resources[user_id] = set()
        self.owned_resources[user_id].add(resource_id)

    def is_owner(self, user_id: UUID, resource_id: UUID) -> bool:
        return (
            user_id in self.owned_resources
            and resource_id in self.owned_resources[user_id]
        )
