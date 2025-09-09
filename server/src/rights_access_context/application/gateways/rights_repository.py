from typing import Protocol
from uuid import UUID

from rights_access_context.domain.value_objects.permission import Permission


class RightsRepository(Protocol):
    def has_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> bool: ...
    def add_permission(
        self, user_id: UUID, resource_id: UUID, permission: Permission = Permission.READ
    ) -> None: ...
    def get_all_permissions(
        self, user_id: UUID, resource_id: UUID
    ) -> set[Permission]: ...
