from uuid import UUID

from shared_kernel.access_control.access_controller import AccessController


class FakeAccessController(AccessController):
    def __init__(self):
        self.granted_accesses = []
        self.access_permissions = {}

    def check_access(self, user_id: UUID, resource_id: UUID) -> bool:
        return self.access_permissions.get(f"{user_id}:{resource_id}", False)

    def grant_access(self, user_id: UUID, resource_id: UUID) -> None:
        self.granted_accesses.append((user_id, resource_id))
        self.access_permissions[f"{user_id}:{resource_id}"] = True

    def add_access_permission(self, user_id: UUID, resource_id: UUID) -> None:
        self.access_permissions[f"{user_id}:{resource_id}"] = True
